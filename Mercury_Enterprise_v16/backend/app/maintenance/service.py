from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..components.models import ComponentInstallationHistory
from ..components.repository import ComponentRepository
from ..fleet.repository import FleetRepository
from ..org.service import OrganizationService
from ..personnel.repository import PersonnelRepository
from ..publications.repository import PublicationRepository
from ..security.operators import operator_store
from .models import (
    AiDocumentIndexStub,
    AiEmbeddingStub,
    AiKnowledgeCrossRef,
    CertificationEvent,
    CriticalTaskPolicy,
    DigitalSignature,
    FaultCode,
    MaintenanceTask,
    TechnicalLogEntry,
)
from .repository import MaintenanceRepository
from .schemas import (
    AiCrossRefCreate,
    AiCrossRefOut,
    AiIndexStubCreate,
    AiIndexStubOut,
    CertificationEventOut,
    CertifyOut,
    CertifyRequest,
    CriticalPolicyCreate,
    CriticalPolicyOut,
    DigitalSignatureOut,
    FaultCodeCreate,
    FaultCodeOut,
    TaskAuditTrailOut,
    TaskCreate,
    TaskOut,
    TaskTransitionRequest,
    TechnicalLogOut,
)

logger = logging.getLogger("mercury.maintenance")

TASK_STATUSES = frozenset(
    {
        "open",
        "assigned",
        "started",
        "in_progress",  # synonym of started (legacy)
        "paused",
        "completed",
        "awaiting_inspection",
        "awaiting_aca",
        "released",
        "closed",
        "rejected",
        "cancelled",
    }
)
CREATABLE_STATUSES = frozenset({"open", "assigned"})
TERMINAL_STATUSES = frozenset({"closed", "rejected", "cancelled"})
TASK_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"assigned", "started", "in_progress", "cancelled", "rejected"}),
    "assigned": frozenset({"started", "in_progress", "paused", "cancelled", "rejected"}),
    "started": frozenset({"paused", "completed", "cancelled", "rejected"}),
    "in_progress": frozenset({"paused", "completed", "cancelled", "rejected", "started"}),
    "paused": frozenset({"started", "in_progress", "cancelled", "rejected"}),
    "completed": frozenset({"closed", "rejected"}),
    "awaiting_inspection": frozenset({"cancelled", "rejected"}),
    "awaiting_aca": frozenset({"cancelled", "rejected"}),
    "released": frozenset({"closed"}),
    "closed": frozenset(),
    "rejected": frozenset(),
    "cancelled": frozenset(),
}
TASK_TYPES = frozenset(
    {
        "scheduled",
        "unscheduled",
        "corrective",
        "preventive",
        "inspection",
        "functional_check",
        "operational_check",
        "troubleshooting",
        "component_replacement",
        "deferred_defect",
        "mel_cdl",
        "service_bulletin",
        "engineering_order",
    }
)
PRIORITIES = frozenset({"low", "normal", "high", "critical"})
CERT_STEPS = (
    "performed",
    "inspected",
    "independent_inspection",
    "aca_certified",
    "aircraft_released",
)
CERT_STEP_SET = frozenset(CERT_STEPS)
SIGN_METHODS = frozenset({"password", "pin", "pki", "smart_card", "biometric_ready"})
POLICY_DOMAINS = frozenset(
    {"engine", "flight_controls", "landing_gear", "fuel", "structural", "propulsion", "general"}
)
CROSS_REF_RELATIONS = frozenset({"related_ata", "related_component", "related_task", "related_fault"})

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _truthy(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in {"1", "true", "yes", "on"}


def _flag(value: bool) -> str:
    return "true" if value else "false"


class MaintenanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MaintenanceRepository(db)
        self.org = OrganizationService(db)
        self.fleet = FleetRepository(db)
        self.personnel = PersonnelRepository(db)
        self.publications = PublicationRepository(db)
        self.components = ComponentRepository(db)

    def ensure_seed_data(self) -> None:
        org_id = "org-aviation-east"
        if self.org.repo.get_organization(org_id) is None:
            return

        pending = False
        now = _utcnow()

        policy_seeds = [
            ("CTP-ENGINE", "Engine Critical Tasks", "engine", True, True, True),
            ("CTP-FLTCTL", "Flight Controls Critical Tasks", "flight_controls", True, True, True),
            ("CTP-LDG", "Landing Gear Critical Tasks", "landing_gear", True, False, True),
        ]
        for code, name, domain, insp, indep, aca in policy_seeds:
            if self.repo.get_critical_policy_by_code(org_id, code) is None:
                self.repo.add_critical_policy(
                    CriticalTaskPolicy(
                        id=f"ctp-{domain.replace('_', '-')}",
                        organization_id=org_id,
                        code=code,
                        name=name,
                        domain=domain,
                        requires_inspector=_flag(insp),
                        requires_independent=_flag(indep),
                        requires_aca=_flag(aca),
                        status="active",
                        created_at=now,
                    )
                )
                pending = True

        if self.repo.get_fault_by_code(org_id, "FC-ENG-OIL") is None:
            self.repo.add_fault_code(
                FaultCode(
                    id="fc-eng-oil",
                    organization_id=org_id,
                    code="FC-ENG-OIL",
                    title="Engine oil pressure fluctuation",
                    ata_chapter_id="ata-71-00",
                    status="active",
                    created_at=now,
                )
            )
            pending = True

        aircraft = self.fleet.get_aircraft("ac-c-gmea", with_registrations=True)
        if aircraft and self.repo.get_task("mtask-demo-c-gmea") is None:
            reg = self.fleet.get_current_registration(aircraft.id)
            policy = self.repo.get_critical_policy_by_code(org_id, "CTP-ENGINE")
            fault = self.repo.get_fault_by_code(org_id, "FC-ENG-OIL")
            pub = self.publications.get_publication("pub-amm-a320-71")
            self.repo.add_task(
                MaintenanceTask(
                    id="mtask-demo-c-gmea",
                    organization_id=org_id,
                    task_number="MT-DEMO-001",
                    task_type="troubleshooting",
                    aircraft_id=aircraft.id,
                    fleet_id=aircraft.fleet_id,
                    registration=reg.registration_mark if reg else "C-GMEA",
                    ata_chapter_id="ata-71-00",
                    title="Investigate engine oil pressure fluctuation",
                    description="Demo open maintenance task for Sprint 7 certification workflow.",
                    priority="high",
                    estimated_hours=Decimal("2.00"),
                    actual_hours=Decimal("0.00"),
                    publication_id="pub-amm-a320-71",
                    publication_revision_id=pub.current_revision_id if pub else None,
                    component_id=None,
                    serial_number="",
                    required_parts="",
                    required_tools="Torque wrench; Oil pressure gauge",
                    required_skills="Powerplant",
                    required_certification="AME",
                    requires_inspector=_flag(True),
                    independent_inspection_required=_flag(True if policy and _truthy(policy.requires_independent) else False),
                    aca_required=_flag(True if policy and _truthy(policy.requires_aca) else True),
                    fault_code_id=fault.id if fault else None,
                    critical_policy_id=policy.id if policy else None,
                    status="open",
                    release_status="not_released",
                    performed_by_employee_id=None,
                    assigned_to_employee_id=None,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            pending = True

        if pending:
            self.repo.commit()

    def _commit_or_conflict(self, *, detail: str) -> None:
        try:
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail=detail) from exc

    def resolve_org_id(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        requested_org_id: str | None,
    ) -> str:
        org_id = (requested_org_id or session_org_id).strip()
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=org_id)
        return org_id

    def assert_org_access(self, *, username: str, session_role: str, organization_id: str) -> None:
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=organization_id)

    # --- serializers ---
    @staticmethod
    def fault_out(row: FaultCode) -> FaultCodeOut:
        return FaultCodeOut(
            id=row.id,
            organization_id=row.organization_id,
            code=row.code,
            title=row.title,
            ata_chapter_id=row.ata_chapter_id,
            status=row.status,
            created_at=row.created_at,
        )

    @staticmethod
    def policy_out(row: CriticalTaskPolicy) -> CriticalPolicyOut:
        return CriticalPolicyOut(
            id=row.id,
            organization_id=row.organization_id,
            code=row.code,
            name=row.name,
            domain=row.domain,
            requires_inspector=_truthy(row.requires_inspector),
            requires_independent=_truthy(row.requires_independent),
            requires_aca=_truthy(row.requires_aca),
            status=row.status,
            created_at=row.created_at,
        )

    @staticmethod
    def task_out(row: MaintenanceTask) -> TaskOut:
        return TaskOut(
            id=row.id,
            organization_id=row.organization_id,
            task_number=row.task_number,
            task_type=row.task_type,
            aircraft_id=row.aircraft_id,
            fleet_id=row.fleet_id,
            registration=row.registration or "",
            ata_chapter_id=row.ata_chapter_id,
            title=row.title,
            description=row.description or "",
            priority=row.priority or "normal",
            due_date=row.due_date,
            estimated_hours=Decimal(str(row.estimated_hours or 0)),
            actual_hours=Decimal(str(row.actual_hours or 0)),
            publication_id=row.publication_id,
            publication_revision_id=row.publication_revision_id,
            component_id=row.component_id,
            serial_number=row.serial_number or "",
            required_parts=row.required_parts or "",
            required_tools=row.required_tools or "",
            required_skills=row.required_skills or "",
            required_certification=row.required_certification or "",
            requires_inspector=_truthy(row.requires_inspector),
            independent_inspection_required=_truthy(row.independent_inspection_required),
            aca_required=_truthy(row.aca_required),
            fault_code_id=row.fault_code_id,
            critical_policy_id=row.critical_policy_id,
            status=row.status,
            release_status=row.release_status or "not_released",
            performed_by_employee_id=row.performed_by_employee_id,
            assigned_to_employee_id=row.assigned_to_employee_id,
            version=int(row.version or 1),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def signature_out(row: DigitalSignature) -> DigitalSignatureOut:
        return DigitalSignatureOut(
            id=row.id,
            organization_id=row.organization_id,
            signer_employee_id=row.signer_employee_id,
            signer_username=row.signer_username or "",
            method=row.method,
            purpose=row.purpose or "",
            target_type=row.target_type,
            target_id=row.target_id,
            signature_hash=row.signature_hash,
            pin_verified=row.pin_verified,
            password_confirmed=row.password_confirmed,
            pki_ready=row.pki_ready,
            smart_card_ready=row.smart_card_ready,
            biometric_ready=row.biometric_ready,
            signed_at=row.signed_at,
            details=row.details or "",
        )

    @staticmethod
    def event_out(row: CertificationEvent) -> CertificationEventOut:
        return CertificationEventOut(
            id=row.id,
            organization_id=row.organization_id,
            task_id=row.task_id,
            step=row.step,
            actor_employee_id=row.actor_employee_id,
            actor_username=row.actor_username or "",
            signature_id=row.signature_id,
            occurred_at=row.occurred_at,
            notes=row.notes or "",
        )

    @staticmethod
    def log_out(row: TechnicalLogEntry) -> TechnicalLogOut:
        return TechnicalLogOut(
            id=row.id,
            organization_id=row.organization_id,
            aircraft_id=row.aircraft_id,
            registration=row.registration or "",
            ata_chapter_id=row.ata_chapter_id,
            task_id=row.task_id,
            publication_id=row.publication_id,
            publication_revision_id=row.publication_revision_id,
            component_id=row.component_id,
            serial_number=row.serial_number or "",
            mechanic_employee_id=row.mechanic_employee_id,
            inspector_employee_id=row.inspector_employee_id,
            independent_inspector_employee_id=getattr(row, "independent_inspector_employee_id", None),
            aca_employee_id=row.aca_employee_id,
            release_signature_id=row.release_signature_id,
            summary=row.summary or "",
            occurred_at=row.occurred_at,
            details=row.details or "",
        )

    @staticmethod
    def index_stub_out(row: AiDocumentIndexStub) -> AiIndexStubOut:
        return AiIndexStubOut(
            id=row.id,
            organization_id=row.organization_id,
            source_type=row.source_type,
            source_id=row.source_id,
            title=row.title or "",
            ata_chapter_id=row.ata_chapter_id,
            status=row.status,
            created_at=row.created_at,
        )

    @staticmethod
    def cross_ref_out(row: AiKnowledgeCrossRef) -> AiCrossRefOut:
        return AiCrossRefOut(
            id=row.id,
            organization_id=row.organization_id,
            from_type=row.from_type,
            from_id=row.from_id,
            to_type=row.to_type,
            to_id=row.to_id,
            relation=row.relation,
            status=row.status,
            created_at=row.created_at,
        )

    def _get_org_task(
        self,
        task_id: str,
        *,
        username: str,
        session_role: str,
        for_update: bool = False,
        with_events: bool = False,
    ) -> MaintenanceTask:
        row = self.repo.get_task(task_id, for_update=for_update, with_events=with_events)
        if row is None:
            raise HTTPException(status_code=404, detail="Maintenance task not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=row.organization_id)
        return row

    # --- fault codes ---
    def list_fault_codes(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
    ) -> list[FaultCodeOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        return [self.fault_out(r) for r in self.repo.list_fault_codes(organization_id=org_id)]

    def create_fault_code(
        self,
        payload: FaultCodeCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> FaultCodeOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        code = payload.code.strip().upper()
        if self.repo.get_fault_by_code(org_id, code):
            raise HTTPException(status_code=409, detail="Fault code already exists")
        row = FaultCode(
            organization_id=org_id,
            code=code,
            title=payload.title.strip(),
            ata_chapter_id=payload.ata_chapter_id,
            status=(payload.status or "active").strip().lower() or "active",
            created_at=_utcnow(),
        )
        self.repo.add_fault_code(row)
        self._commit_or_conflict(detail="Fault code conflict")
        self.repo.refresh(row)
        return self.fault_out(row)

    # --- critical policies ---
    def list_critical_policies(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
    ) -> list[CriticalPolicyOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        return [self.policy_out(r) for r in self.repo.list_critical_policies(organization_id=org_id)]

    def create_critical_policy(
        self,
        payload: CriticalPolicyCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> CriticalPolicyOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        if payload.domain not in POLICY_DOMAINS:
            raise HTTPException(status_code=400, detail="Invalid critical policy domain")
        code = payload.code.strip().upper()
        if self.repo.get_critical_policy_by_code(org_id, code):
            raise HTTPException(status_code=409, detail="Critical policy code already exists")
        row = CriticalTaskPolicy(
            organization_id=org_id,
            code=code,
            name=payload.name.strip(),
            domain=payload.domain,
            requires_inspector=_flag(payload.requires_inspector),
            requires_independent=_flag(payload.requires_independent),
            requires_aca=_flag(payload.requires_aca),
            status=(payload.status or "active").strip().lower() or "active",
            created_at=_utcnow(),
        )
        self.repo.add_critical_policy(row)
        self._commit_or_conflict(detail="Critical policy conflict")
        self.repo.refresh(row)
        return self.policy_out(row)

    # --- tasks ---
    def list_tasks(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
        aircraft_id: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        priority: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TaskOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        rows = self.repo.list_tasks(
            organization_id=org_id,
            aircraft_id=aircraft_id,
            status=status,
            task_type=task_type,
            priority=priority,
            limit=limit,
            offset=offset,
        )
        return [self.task_out(r) for r in rows]

    def get_task(self, task_id: str, *, username: str, session_role: str) -> TaskOut:
        return self.task_out(self._get_org_task(task_id, username=username, session_role=session_role))

    def get_task_audit_trail(
        self, task_id: str, *, username: str, session_role: str
    ) -> TaskAuditTrailOut:
        task = self._get_org_task(task_id, username=username, session_role=session_role, with_events=True)
        events = self.repo.list_certification_events(task.id)
        sig_ids = [e.signature_id for e in events if e.signature_id]
        signatures = self.repo.list_signatures_by_ids(sig_ids) if sig_ids else []
        logs = self.repo.list_logbook_for_task(task.id)
        return TaskAuditTrailOut(
            task=self.task_out(task),
            certification_events=[self.event_out(e) for e in events],
            signatures=[self.signature_out(s) for s in signatures],
            logbook_entries=[self.log_out(e) for e in logs],
        )

    def create_task(
        self,
        payload: TaskCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> TaskOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        status_value = (payload.status or "open").strip().lower()
        if status_value not in CREATABLE_STATUSES:
            raise HTTPException(status_code=400, detail="Tasks may only be created as open or assigned")
        task_type = (payload.task_type or "corrective").strip().lower()
        if task_type not in TASK_TYPES:
            raise HTTPException(status_code=400, detail="Invalid task_type")
        priority = (payload.priority or "normal").strip().lower()
        if priority not in PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid priority")

        aircraft = self.fleet.get_aircraft(payload.aircraft_id)
        if aircraft is None or aircraft.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Aircraft not found in organization")

        assigned_to = payload.assigned_to_employee_id
        if assigned_to:
            assignee = self.personnel.get_employee(assigned_to)
            if assignee is None or assignee.organization_id != org_id or assignee.status != "active":
                raise HTTPException(status_code=404, detail="Assigned employee not found in organization")
            if status_value == "open":
                status_value = "assigned"

        policy = None
        if payload.critical_policy_id:
            policy = self.repo.get_critical_policy(payload.critical_policy_id)
            if policy is None or policy.organization_id != org_id:
                raise HTTPException(status_code=404, detail="Critical policy not found")
        if payload.fault_code_id:
            fault = self.repo.get_fault_code(payload.fault_code_id)
            if fault is None or fault.organization_id != org_id:
                raise HTTPException(status_code=404, detail="Fault code not found")

        publication_id = payload.publication_id
        publication_revision_id = payload.publication_revision_id
        if publication_id:
            pub = self.publications.get_publication(publication_id)
            if pub is None or pub.organization_id != org_id or pub.status == "archived":
                raise HTTPException(status_code=404, detail="Publication not found in organization")
            if publication_revision_id:
                rev = self.publications.get_revision(publication_revision_id)
                if rev is None or rev.publication_id != pub.id:
                    raise HTTPException(status_code=404, detail="Publication revision not found")
            else:
                publication_revision_id = pub.current_revision_id

        serial_number = (payload.serial_number or "").strip()
        component_id = payload.component_id
        if component_id:
            component = self.components.get_component(component_id)
            if component is None or component.organization_id != org_id:
                raise HTTPException(status_code=404, detail="Component not found in organization")
            if not serial_number:
                serial_number = component.serial_number

        # Certification flags: explicit payload overrides, else critical policy, else safe defaults.
        requires_inspector = (
            payload.requires_inspector
            if payload.requires_inspector is not None
            else (_truthy(policy.requires_inspector) if policy else True)
        )
        independent_required = (
            payload.independent_inspection_required
            if payload.independent_inspection_required is not None
            else (_truthy(policy.requires_independent) if policy else False)
        )
        aca_required = (
            payload.aca_required
            if payload.aca_required is not None
            else (_truthy(policy.requires_aca) if policy else False)
        )

        task_number = (payload.task_number or "").strip().upper()
        if not task_number:
            task_number = f"MT-{uuid.uuid4().hex[:8].upper()}"
        if self.repo.get_task_by_number(org_id, task_number):
            raise HTTPException(status_code=409, detail="Task number already exists in organization")

        reg = self.fleet.get_current_registration(aircraft.id)
        now = _utcnow()
        row = MaintenanceTask(
            organization_id=org_id,
            task_number=task_number,
            task_type=task_type,
            aircraft_id=aircraft.id,
            fleet_id=aircraft.fleet_id,
            registration=reg.registration_mark if reg else "",
            ata_chapter_id=payload.ata_chapter_id,
            title=payload.title.strip(),
            description=(payload.description or "").strip(),
            priority=priority,
            due_date=payload.due_date,
            estimated_hours=payload.estimated_hours or Decimal("0.00"),
            actual_hours=payload.actual_hours or Decimal("0.00"),
            publication_id=publication_id,
            publication_revision_id=publication_revision_id,
            component_id=component_id,
            serial_number=serial_number,
            required_parts=(payload.required_parts or "").strip(),
            required_tools=(payload.required_tools or "").strip(),
            required_skills=(payload.required_skills or "").strip(),
            required_certification=(payload.required_certification or "").strip(),
            requires_inspector=_flag(requires_inspector),
            independent_inspection_required=_flag(independent_required),
            aca_required=_flag(aca_required),
            fault_code_id=payload.fault_code_id,
            critical_policy_id=payload.critical_policy_id,
            status=status_value,
            release_status="not_released",
            performed_by_employee_id=payload.performed_by_employee_id,
            assigned_to_employee_id=assigned_to,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.repo.add_task(row)
        self._commit_or_conflict(detail="Maintenance task conflict")
        self.repo.refresh(row)
        return self.task_out(row)

    def transition_task(
        self,
        task_id: str,
        payload: TaskTransitionRequest,
        *,
        username: str,
        session_role: str,
    ) -> TaskOut:
        task = self._get_org_task(task_id, username=username, session_role=session_role, for_update=True)
        if payload.expected_version is not None and int(task.version or 1) != payload.expected_version:
            raise HTTPException(status_code=409, detail="Task version conflict")
        current = (task.status or "open").strip().lower()
        target = payload.to_status.strip().lower()
        if target == "in_progress":
            target = "started"
        allowed = TASK_TRANSITIONS.get(current, frozenset())
        if current == "in_progress":
            allowed = TASK_TRANSITIONS["started"] | allowed
        if target not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"Invalid transition from '{current}' to '{target}'",
            )
        if target == "assigned" or payload.assigned_to_employee_id:
            emp_id = payload.assigned_to_employee_id or task.assigned_to_employee_id
            if not emp_id:
                raise HTTPException(status_code=400, detail="assigned_to_employee_id required")
            employee = self.personnel.get_employee(emp_id)
            if employee is None or employee.organization_id != task.organization_id or employee.status != "active":
                raise HTTPException(status_code=404, detail="Assigned employee not found in organization")
            task.assigned_to_employee_id = employee.id
        task.status = target
        task.version = int(task.version or 1) + 1
        task.updated_at = _utcnow()
        self._commit_or_conflict(detail="Task transition conflict")
        self.repo.refresh(task)
        return self.task_out(task)

    def _required_steps_for_task(self, task: MaintenanceTask) -> list[str]:
        """Single source of truth: task-level flags (policy copied at create time)."""
        steps = ["performed"]
        if _truthy(task.requires_inspector):
            steps.append("inspected")
        if _truthy(task.independent_inspection_required):
            steps.append("independent_inspection")
        if _truthy(task.aca_required):
            steps.append("aca_certified")
        steps.append("aircraft_released")
        return steps

    def _auth_active(self, employee_id: str, auth_type: str, *, now: datetime) -> bool:
        for auth in self.personnel.list_authorizations(employee_id):
            if auth.auth_type != auth_type or auth.status != "active":
                continue
            if auth.expires_at is not None and auth.expires_at < now:
                continue
            return True
        return False

    def _qual_active(self, employee_id: str, allowed_types: set[str], *, now: datetime) -> bool:
        for qual in self.personnel.list_qualifications(employee_id):
            if qual.qualification_type not in allowed_types or qual.status != "active":
                continue
            if qual.expires_at is not None and qual.expires_at < now:
                continue
            return True
        return False

    def _assert_signer_binding(self, *, employee, username: str, session_role: str) -> None:
        linked = (employee.user_username or "").strip().lower()
        actor = username.strip().lower()
        if linked:
            if linked != actor and session_role != "Administrator":
                raise HTTPException(
                    status_code=403,
                    detail="Cannot certify as an employee linked to a different user",
                )
        elif session_role != "Administrator":
            raise HTTPException(
                status_code=403,
                detail="Employee must be linked to the session user to certify",
            )

    def _assert_credential(self, *, payload: CertifyRequest, username: str, employee_id: str) -> None:
        if payload.method == "password":
            credential = (payload.credential or "").strip()
            if not credential:
                raise HTTPException(status_code=400, detail="Password credential required")
            if operator_store.authenticate(username, credential) is None:
                raise HTTPException(status_code=401, detail="Invalid password credential")
        elif payload.method == "pin":
            credential = (payload.credential or "").strip()
            if not credential:
                raise HTTPException(status_code=400, detail="PIN credential required")
            stamps = [s for s in self.personnel.list_stamps(employee_id) if s.status == "active"]
            if not any(hmac.compare_digest(str(s.stamp_code), credential) for s in stamps):
                raise HTTPException(status_code=401, detail="Invalid PIN credential")
        # pki / smart_card / biometric_ready: provider stubs — no live verification yet

    def _assert_step_authority(
        self,
        *,
        step: str,
        employee_id: str,
        prior_events: list[CertificationEvent],
        now: datetime,
    ) -> None:
        by_step = {e.step: e for e in prior_events}
        if step == "performed":
            if not self._qual_active(
                employee_id, {"ame_license", "rating", "type_rating", "training"}, now=now
            ):
                raise HTTPException(status_code=403, detail="Active maintenance qualification required")
        elif step == "inspected":
            if not (
                self._qual_active(employee_id, {"ame_license", "rating", "type_rating"}, now=now)
                or self._auth_active(employee_id, "stamp", now=now)
            ):
                raise HTTPException(status_code=403, detail="Inspector qualification or stamp required")
        elif step == "independent_inspection":
            if not self._auth_active(employee_id, "independent_inspection", now=now):
                raise HTTPException(status_code=403, detail="Independent inspection authorization required")
            performed = by_step.get("performed")
            if performed and performed.actor_employee_id == employee_id:
                raise HTTPException(
                    status_code=409,
                    detail="Independent inspector must differ from the performing technician",
                )
            inspected = by_step.get("inspected")
            if inspected and inspected.actor_employee_id == employee_id:
                raise HTTPException(
                    status_code=409,
                    detail="Independent inspector must differ from the inspector",
                )
        elif step in {"aca_certified", "aircraft_released"}:
            if not self._auth_active(employee_id, "aca", now=now):
                raise HTTPException(status_code=403, detail="Active ACA authorization required")

    def _canonical_signature_payload(
        self,
        *,
        organization_id: str,
        task_id: str,
        step: str,
        employee_id: str,
        username: str,
        method: str,
        signed_at: datetime,
        notes: str,
    ) -> str:
        return "|".join(
            [
                organization_id,
                task_id,
                step,
                employee_id,
                username,
                method,
                signed_at.isoformat(),
                notes.strip(),
            ]
        )

    def sign_action(
        self,
        task_id: str,
        payload: CertifyRequest,
        *,
        username: str,
        session_role: str,
    ) -> CertifyOut:
        if payload.step not in CERT_STEP_SET:
            raise HTTPException(status_code=400, detail="Invalid certification step")
        if payload.method not in SIGN_METHODS:
            raise HTTPException(status_code=400, detail="Invalid signature method")

        task = self._get_org_task(
            task_id, username=username, session_role=session_role, for_update=True, with_events=True
        )
        if task.status in TERMINAL_STATUSES or task.status == "released":
            raise HTTPException(status_code=409, detail="Task is already finalized")
        if payload.expected_version is not None and int(task.version or 1) != payload.expected_version:
            raise HTTPException(status_code=409, detail="Task version conflict")

        employee = self.personnel.get_employee(payload.employee_id)
        if employee is None or employee.organization_id != task.organization_id or employee.status != "active":
            raise HTTPException(status_code=404, detail="Employee not found in organization")

        self._assert_signer_binding(employee=employee, username=username, session_role=session_role)
        self._assert_credential(payload=payload, username=username, employee_id=employee.id)

        prior_events = self.repo.list_certification_events(task.id)
        existing_steps = {e.step for e in prior_events}
        if payload.step in existing_steps:
            raise HTTPException(status_code=409, detail=f"Step already completed: {payload.step}")

        required = self._required_steps_for_task(task)
        if payload.step not in required:
            raise HTTPException(
                status_code=400,
                detail=f"Step {payload.step} is not required by task certification settings",
            )
        next_index = len([s for s in required if s in existing_steps])
        expected = required[next_index]
        if payload.step != expected:
            raise HTTPException(
                status_code=409,
                detail=f"Workflow order violation: expected step '{expected}'",
            )

        now = _utcnow()
        self._assert_step_authority(
            step=payload.step, employee_id=employee.id, prior_events=prior_events, now=now
        )
        notes = (payload.notes or "").strip()
        actor_username = employee.user_username or username
        canonical = self._canonical_signature_payload(
            organization_id=task.organization_id,
            task_id=task.id,
            step=payload.step,
            employee_id=employee.id,
            username=actor_username,
            method=payload.method,
            signed_at=now,
            notes=notes,
        )
        signature_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        signature = DigitalSignature(
            organization_id=task.organization_id,
            signer_employee_id=employee.id,
            signer_username=actor_username,
            method=payload.method,
            purpose=f"certification.{payload.step}",
            target_type="maintenance_task",
            target_id=task.id,
            signature_hash=signature_hash,
            pin_verified=_flag(bool(payload.credential) and payload.method == "pin"),
            password_confirmed=_flag(bool(payload.credential) and payload.method == "password"),
            pki_ready=_flag(payload.method == "pki"),
            smart_card_ready=_flag(payload.method == "smart_card"),
            biometric_ready=_flag(payload.method == "biometric_ready"),
            signed_at=now,
            details=notes,
        )
        self.repo.add_signature(signature)
        self.repo.flush()

        event = CertificationEvent(
            organization_id=task.organization_id,
            task_id=task.id,
            step=payload.step,
            actor_employee_id=employee.id,
            actor_username=actor_username,
            signature_id=signature.id,
            occurred_at=now,
            notes=notes,
        )
        self.repo.add_certification_event(event)

        if payload.actual_hours is not None:
            task.actual_hours = payload.actual_hours

        if payload.step == "performed":
            task.performed_by_employee_id = employee.id
            task.status = "started"
        elif payload.step == "inspected":
            task.status = "awaiting_inspection"
        elif payload.step == "independent_inspection":
            task.status = "awaiting_inspection"
        elif payload.step == "aca_certified":
            task.status = "awaiting_aca"
        elif payload.step == "aircraft_released":
            task.status = "released"
            task.release_status = "released"

        # Advance status toward next awaiting gate when intermediate steps complete.
        completed = existing_steps | {payload.step}
        remaining = [s for s in required if s not in completed]
        if remaining and payload.step != "aircraft_released":
            nxt = remaining[0]
            if nxt in {"inspected", "independent_inspection"}:
                task.status = "awaiting_inspection"
            elif nxt == "aca_certified":
                task.status = "awaiting_aca"
            elif nxt == "aircraft_released":
                if "aca_certified" in completed:
                    task.status = "awaiting_aca"
                elif "inspected" in completed or "independent_inspection" in completed:
                    task.status = "completed"
                else:
                    task.status = "started"

        log_entry_id: str | None = None
        if payload.step == "aircraft_released":
            events = prior_events + [event]
            by_step = {e.step: e for e in events}
            log_row = TechnicalLogEntry(
                organization_id=task.organization_id,
                aircraft_id=task.aircraft_id,
                registration=task.registration or "",
                ata_chapter_id=task.ata_chapter_id,
                task_id=task.id,
                publication_id=task.publication_id,
                publication_revision_id=task.publication_revision_id,
                component_id=task.component_id,
                serial_number=task.serial_number or "",
                mechanic_employee_id=(
                    by_step["performed"].actor_employee_id if "performed" in by_step else task.performed_by_employee_id
                ),
                inspector_employee_id=(
                    by_step["inspected"].actor_employee_id if "inspected" in by_step else None
                ),
                independent_inspector_employee_id=(
                    by_step["independent_inspection"].actor_employee_id
                    if "independent_inspection" in by_step
                    else None
                ),
                aca_employee_id=(
                    by_step["aca_certified"].actor_employee_id if "aca_certified" in by_step else None
                ),
                release_signature_id=signature.id,
                summary=f"{task.task_number}: {task.title}",
                occurred_at=now,
                details=(
                    f"aircraft_history=true;maintenance_log=true;"
                    f"task_type={task.task_type};priority={task.priority};"
                    f"publication={task.publication_id or ''};revision={task.publication_revision_id or ''};"
                    f"signature_chain={','.join(e.signature_id or '' for e in events)};"
                    f"{notes or task.description or ''}"
                ),
            )
            self.repo.add_log_entry(log_row)
            self.repo.flush()
            log_entry_id = log_row.id
            task.status = "released"
            task.release_status = "released"
            if task.component_id:
                component = self.components.get_component(task.component_id)
                if component is not None and component.organization_id == task.organization_id:
                    self.components.add_history(
                        ComponentInstallationHistory(
                            organization_id=task.organization_id,
                            component_id=component.id,
                            event_type="maintenance_release",
                            aircraft_id=task.aircraft_id,
                            from_aircraft_id=None,
                            to_aircraft_id=None,
                            position=component.installation_position,
                            from_status=component.component_status,
                            to_status=component.component_status,
                            occurred_at=now,
                            aircraft_hours=None,
                            aircraft_cycles=None,
                            actor=actor_username,
                            reason="task_release",
                            reference=task.task_number,
                            details=f"task_id={task.id};log_entry_id={log_entry_id}",
                        )
                    )

        task.version = int(task.version or 1) + 1
        task.updated_at = now
        self._commit_or_conflict(detail="Certification conflict")
        self.repo.refresh(task)
        self.repo.refresh(signature)
        self.repo.refresh(event)
        return CertifyOut(
            task=self.task_out(task),
            signature=self.signature_out(signature),
            event=self.event_out(event),
            log_entry_id=log_entry_id,
        )

    def get_signature(self, signature_id: str, *, username: str, session_role: str) -> DigitalSignatureOut:
        row = self.repo.get_signature(signature_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Signature not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=row.organization_id)
        return self.signature_out(row)

    def list_logbook(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
        aircraft_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TechnicalLogOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        return [
            self.log_out(r)
            for r in self.repo.list_logbook(
                organization_id=org_id, aircraft_id=aircraft_id, limit=limit, offset=offset
            )
        ]

    # --- AI stubs ---
    def list_index_stubs(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
    ) -> list[AiIndexStubOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        return [self.index_stub_out(r) for r in self.repo.list_index_stubs(organization_id=org_id)]

    def create_index_stub(
        self,
        payload: AiIndexStubCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> AiIndexStubOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        now = _utcnow()
        stub = AiDocumentIndexStub(
            organization_id=org_id,
            source_type=payload.source_type.strip(),
            source_id=payload.source_id.strip(),
            title=(payload.title or "").strip(),
            ata_chapter_id=payload.ata_chapter_id,
            status="pending_index",
            created_at=now,
        )
        self.repo.add_index_stub(stub)
        self.repo.flush()
        # Placeholder embedding row only — never compute vectors.
        self.repo.add_embedding_stub(
            AiEmbeddingStub(
                index_id=stub.id,
                model_name="",
                dimensions=0,
                status="not_computed",
                created_at=now,
            )
        )
        self._commit_or_conflict(detail="AI index stub conflict")
        self.repo.refresh(stub)
        return self.index_stub_out(stub)

    def list_cross_refs(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
    ) -> list[AiCrossRefOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        return [self.cross_ref_out(r) for r in self.repo.list_cross_refs(organization_id=org_id)]

    def create_cross_ref(
        self,
        payload: AiCrossRefCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> AiCrossRefOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        if payload.relation not in CROSS_REF_RELATIONS:
            raise HTTPException(status_code=400, detail="Invalid cross-ref relation")
        row = AiKnowledgeCrossRef(
            organization_id=org_id,
            from_type=payload.from_type.strip(),
            from_id=payload.from_id.strip(),
            to_type=payload.to_type.strip(),
            to_id=payload.to_id.strip(),
            relation=payload.relation,
            status=(payload.status or "active").strip().lower() or "active",
            created_at=_utcnow(),
        )
        self.repo.add_cross_ref(row)
        self._commit_or_conflict(detail="AI cross-ref conflict")
        self.repo.refresh(row)
        return self.cross_ref_out(row)
