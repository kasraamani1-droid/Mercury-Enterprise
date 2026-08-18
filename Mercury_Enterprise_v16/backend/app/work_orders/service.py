from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..fleet.repository import FleetRepository
from ..maintenance.schemas import CertifyRequest, TaskCreate
from ..maintenance.service import MaintenanceService
from ..org.service import OrganizationService
from ..personnel.repository import PersonnelRepository
from ..platform.event_framework import event_framework
from ..publications.repository import PublicationRepository
from ..security.authorization import has_permissions
from .models import JobCard, JobCardAttachment, WorkOrder, WorkPackage
from .repository import WorkOrderRepository
from .schemas import (
    ExecutionDashboardOut,
    JobCardAssignRequest,
    JobCardAttachmentCreate,
    JobCardAttachmentOut,
    JobCardCreate,
    JobCardInspectRequest,
    JobCardOut,
    JobCardReleaseRequest,
    JobCardTransitionRequest,
    ReportSummaryOut,
    WorkOrderCreate,
    WorkOrderOut,
    WorkPackageCreate,
    WorkPackageOut,
)

logger = logging.getLogger("mercury.work_orders")

PACKAGE_STATUSES = frozenset(
    {"draft", "planned", "in_progress", "completed", "released", "closed", "cancelled"}
)
ORDER_STATUSES = frozenset(
    {"draft", "open", "in_progress", "delayed", "completed", "released", "closed", "cancelled"}
)
JC_STATUSES = frozenset(
    {
        "draft",
        "assigned",
        "accepted",
        "in_progress",
        "paused",
        "waiting_parts",
        "waiting_engineering",
        "waiting_inspection",
        "completed",
        "rejected",
        "released",
        "closed",
    }
)
PRIORITIES = frozenset({"low", "normal", "high", "critical"})

# Certification gates (waiting_inspection / completed / released) are NOT reachable via
# /transition — only via complete-work, inspect, and release endpoints.
JC_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"assigned", "closed"}),
    "assigned": frozenset({"accepted", "draft", "closed"}),
    "accepted": frozenset({"in_progress", "waiting_parts", "waiting_engineering", "closed"}),
    "in_progress": frozenset({"paused", "waiting_parts", "waiting_engineering", "closed"}),
    "paused": frozenset({"in_progress", "waiting_parts", "waiting_engineering", "closed"}),
    "waiting_parts": frozenset({"in_progress", "accepted", "closed"}),
    "waiting_engineering": frozenset({"in_progress", "accepted", "closed"}),
    "waiting_inspection": frozenset(),  # inspect approve/reject/rework only
    "completed": frozenset(),  # ACA release endpoint only
    "rejected": frozenset({"in_progress", "assigned", "closed"}),
    "released": frozenset({"closed"}),  # supervisor/planner manage required
    "closed": frozenset(),
}
CERT_GATED_STATUSES = frozenset({"waiting_inspection", "completed", "released"})
TERMINAL_MUTATION_BLOCK = frozenset({"released", "closed"})


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


class WorkOrderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = WorkOrderRepository(db)
        self.org = OrganizationService(db)
        self.fleet = FleetRepository(db)
        self.personnel = PersonnelRepository(db)
        self.publications = PublicationRepository(db)
        self.maintenance = MaintenanceService(db)

    def ensure_seed_data(self) -> None:
        """Idempotent demo package / order / job card (create any missing row)."""
        org_id = "org-aviation-east"
        if self.org.repo.get_organization(org_id) is None:
            return
        aircraft = self.fleet.get_aircraft("ac-c-gmea")
        if aircraft is None:
            return
        now = _utcnow()
        reg = self.fleet.get_current_registration(aircraft.id)
        planner = self.personnel.get_by_org_number(org_id, "E-1001")
        pub = self.publications.get_publication("pub-amm-a320-71")
        pub_rev = pub.current_revision_id if pub else None
        task = self.maintenance.repo.get_task("mtask-demo-c-gmea")
        created = False

        package = self.repo.get_package("wp-demo-c-gmea") or self.repo.get_package_by_number(
            org_id, "WP-DEMO-001"
        )
        if package is None:
            package = WorkPackage(
                id="wp-demo-c-gmea",
                organization_id=org_id,
                package_number="WP-DEMO-001",
                fleet_id=aircraft.fleet_id,
                aircraft_id=aircraft.id,
                registration=reg.registration_mark if reg else "C-GMEA",
                description="Demo A-check work package for Sprint 8",
                status="planned",
                priority="high",
                scheduled_start=now,
                planner_employee_id=planner.id if planner else None,
                supervisor_employee_id=planner.id if planner else None,
                hangar_bay="Bay-1",
                shift_code="DAY",
                estimated_hours=Decimal("8.00"),
                actual_hours=Decimal("0.00"),
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.repo.add_package(package)
            self.repo.flush()
            created = True

        order = self.repo.get_order("wo-demo-powerplant") or self.repo.get_order_by_number(
            org_id, "WO-DEMO-7100"
        )
        if order is None:
            order = WorkOrder(
                id="wo-demo-powerplant",
                organization_id=org_id,
                work_package_id=package.id,
                wo_number="WO-DEMO-7100",
                aircraft_id=aircraft.id,
                ata_chapter_id="ata-71-00",
                title="Powerplant inspection package",
                description="Demo work order linked to AMM powerplant",
                status="open",
                priority="high",
                planner_employee_id=planner.id if planner else None,
                supervisor_employee_id=planner.id if planner else None,
                publication_id="pub-amm-a320-71",
                publication_revision_id=pub_rev,
                estimated_hours=Decimal("4.00"),
                actual_hours=Decimal("0.00"),
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.repo.add_order(order)
            self.repo.flush()
            created = True

        card = self.repo.get_job_card("jc-demo-oil") or self.repo.get_job_card_by_number(
            org_id, "JC-DEMO-001"
        )
        if card is None:
            card = JobCard(
                id="jc-demo-oil",
                organization_id=org_id,
                work_order_id=order.id,
                job_card_number="JC-DEMO-001",
                maintenance_task_id=task.id if task else None,
                aircraft_id=aircraft.id,
                ata_chapter_id="ata-71-00",
                title="Investigate engine oil pressure fluctuation",
                description="Demo job card for technician execution",
                status="assigned" if planner else "draft",
                priority="high",
                publication_id="pub-amm-a320-71",
                publication_revision_id=order.publication_revision_id,
                required_tools="Torque wrench; Oil pressure gauge",
                required_skills="Powerplant",
                required_certification="AME",
                estimated_hours=Decimal("2.00"),
                actual_hours=Decimal("0.00"),
                technician_employee_id=planner.id if planner else None,
                hangar_bay="Bay-1",
                independent_inspection_required=_flag(True),
                aca_required=_flag(True),
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.repo.add_job_card(card)
            created = True

        if created:
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

    def package_out(self, row: WorkPackage) -> WorkPackageOut:
        return WorkPackageOut(
            id=row.id,
            organization_id=row.organization_id,
            package_number=row.package_number,
            fleet_id=row.fleet_id,
            aircraft_id=row.aircraft_id,
            registration=row.registration or "",
            description=row.description or "",
            status=row.status,
            priority=row.priority,
            scheduled_start=row.scheduled_start,
            scheduled_finish=row.scheduled_finish,
            actual_start=row.actual_start,
            actual_finish=row.actual_finish,
            planner_employee_id=row.planner_employee_id,
            supervisor_employee_id=row.supervisor_employee_id,
            hangar_bay=row.hangar_bay or "",
            shift_code=row.shift_code or "",
            estimated_hours=Decimal(str(row.estimated_hours or 0)),
            actual_hours=Decimal(str(row.actual_hours or 0)),
            work_order_count=self.repo.count_orders_in_package(row.id),
            version=int(row.version or 1),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def order_out(self, row: WorkOrder) -> WorkOrderOut:
        return WorkOrderOut(
            id=row.id,
            organization_id=row.organization_id,
            work_package_id=row.work_package_id,
            wo_number=row.wo_number,
            aircraft_id=row.aircraft_id,
            ata_chapter_id=row.ata_chapter_id,
            title=row.title,
            description=row.description or "",
            status=row.status,
            priority=row.priority,
            planner_employee_id=row.planner_employee_id,
            supervisor_employee_id=row.supervisor_employee_id,
            publication_id=row.publication_id,
            publication_revision_id=row.publication_revision_id,
            due_date=row.due_date,
            estimated_hours=Decimal(str(row.estimated_hours or 0)),
            actual_hours=Decimal(str(row.actual_hours or 0)),
            job_card_count=self.repo.count_cards_in_order(row.id),
            version=int(row.version or 1),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def job_card_out(self, row: JobCard) -> JobCardOut:
        return JobCardOut(
            id=row.id,
            organization_id=row.organization_id,
            work_order_id=row.work_order_id,
            job_card_number=row.job_card_number,
            maintenance_task_id=row.maintenance_task_id,
            aircraft_id=row.aircraft_id,
            ata_chapter_id=row.ata_chapter_id,
            title=row.title,
            description=row.description or "",
            status=row.status,
            priority=row.priority,
            publication_id=row.publication_id,
            publication_revision_id=row.publication_revision_id,
            component_id=row.component_id,
            required_parts=row.required_parts or "",
            required_tools=row.required_tools or "",
            required_skills=row.required_skills or "",
            required_certification=row.required_certification or "",
            estimated_hours=Decimal(str(row.estimated_hours or 0)),
            actual_hours=Decimal(str(row.actual_hours or 0)),
            technician_employee_id=row.technician_employee_id,
            inspector_employee_id=row.inspector_employee_id,
            independent_inspector_employee_id=row.independent_inspector_employee_id,
            aca_employee_id=row.aca_employee_id,
            hangar_bay=row.hangar_bay or "",
            notes=row.notes or "",
            rework_reason=row.rework_reason or "",
            independent_inspection_required=_truthy(row.independent_inspection_required),
            aca_required=_truthy(row.aca_required),
            version=int(row.version or 1),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def attachment_out(row: JobCardAttachment) -> JobCardAttachmentOut:
        return JobCardAttachmentOut(
            id=row.id,
            organization_id=row.organization_id,
            job_card_id=row.job_card_id,
            kind=row.kind,
            title=row.title or "",
            storage_uri=row.storage_uri or "",
            content_type=row.content_type or "",
            notes=row.notes or "",
            created_by=row.created_by or "",
            created_at=row.created_at,
        )

    def _get_org_package(self, package_id: str, *, username: str, session_role: str, for_update: bool = False) -> WorkPackage:
        row = self.repo.get_package(package_id, for_update=for_update)
        if row is None:
            raise HTTPException(status_code=404, detail="Work package not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=row.organization_id)
        return row

    def _get_org_order(self, order_id: str, *, username: str, session_role: str, for_update: bool = False) -> WorkOrder:
        row = self.repo.get_order(order_id, for_update=for_update)
        if row is None:
            raise HTTPException(status_code=404, detail="Work order not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=row.organization_id)
        return row

    def _get_org_card(
        self, job_card_id: str, *, username: str, session_role: str, for_update: bool = False
    ) -> JobCard:
        row = self.repo.get_job_card(job_card_id, for_update=for_update)
        if row is None:
            raise HTTPException(status_code=404, detail="Job card not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=row.organization_id)
        return row

    def _employee_in_org(self, employee_id: str | None, org_id: str) -> None:
        if not employee_id:
            return
        emp = self.personnel.get_employee(employee_id)
        if emp is None or emp.organization_id != org_id or emp.status != "active":
            raise HTTPException(status_code=404, detail="Employee not found in organization")

    # --- packages ---
    def list_packages(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[WorkPackageOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        rows = self.repo.list_packages(
            organization_id=org_id,
            aircraft_id=filters.get("aircraft_id"),
            status=filters.get("status"),
            limit=int(filters.get("limit") or 100),
            offset=int(filters.get("offset") or 0),
        )
        return [self.package_out(r) for r in rows]

    def create_package(
        self,
        payload: WorkPackageCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> WorkPackageOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        priority = (payload.priority or "normal").strip().lower()
        if priority not in PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid priority")
        aircraft = self.fleet.get_aircraft(payload.aircraft_id)
        if aircraft is None or aircraft.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Aircraft not found in organization")
        self._employee_in_org(payload.planner_employee_id, org_id)
        self._employee_in_org(payload.supervisor_employee_id, org_id)
        number = (payload.package_number or "").strip().upper() or f"WP-{uuid.uuid4().hex[:8].upper()}"
        if self.repo.get_package_by_number(org_id, number):
            raise HTTPException(status_code=409, detail="Package number already exists")
        reg = self.fleet.get_current_registration(aircraft.id)
        now = _utcnow()
        row = WorkPackage(
            organization_id=org_id,
            package_number=number,
            fleet_id=aircraft.fleet_id,
            aircraft_id=aircraft.id,
            registration=reg.registration_mark if reg else "",
            description=(payload.description or "").strip(),
            status="draft",
            priority=priority,
            scheduled_start=payload.scheduled_start,
            scheduled_finish=payload.scheduled_finish,
            planner_employee_id=payload.planner_employee_id,
            supervisor_employee_id=payload.supervisor_employee_id,
            hangar_bay=(payload.hangar_bay or "").strip(),
            shift_code=(payload.shift_code or "").strip(),
            estimated_hours=payload.estimated_hours or Decimal("0.00"),
            actual_hours=Decimal("0.00"),
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.repo.add_package(row)
        self._commit_or_conflict(detail="Work package conflict")
        self.repo.refresh(row)
        return self.package_out(row)

    def get_package(self, package_id: str, *, username: str, session_role: str) -> WorkPackageOut:
        return self.package_out(self._get_org_package(package_id, username=username, session_role=session_role))

    # --- work orders ---
    def list_orders(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[WorkOrderOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        rows = self.repo.list_orders(
            organization_id=org_id,
            work_package_id=filters.get("work_package_id"),
            aircraft_id=filters.get("aircraft_id"),
            status=filters.get("status"),
            limit=int(filters.get("limit") or 100),
            offset=int(filters.get("offset") or 0),
        )
        return [self.order_out(r) for r in rows]

    def create_order(
        self,
        payload: WorkOrderCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> WorkOrderOut:
        package = self._get_org_package(
            payload.work_package_id, username=username, session_role=session_role, for_update=True
        )
        org_id = package.organization_id
        if payload.organization_id and payload.organization_id != org_id:
            raise HTTPException(status_code=400, detail="organization_id mismatch with package")
        priority = (payload.priority or "normal").strip().lower()
        if priority not in PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid priority")
        self._employee_in_org(payload.planner_employee_id, org_id)
        self._employee_in_org(payload.supervisor_employee_id, org_id)
        publication_id = payload.publication_id
        publication_revision_id = payload.publication_revision_id
        if publication_id:
            pub = self.publications.get_publication(publication_id)
            if pub is None or pub.organization_id != org_id or pub.status == "archived":
                raise HTTPException(status_code=404, detail="Publication not found")
            if publication_revision_id:
                rev = self.publications.get_revision(publication_revision_id)
                if rev is None or rev.publication_id != pub.id:
                    raise HTTPException(status_code=404, detail="Publication revision not found")
            else:
                publication_revision_id = pub.current_revision_id
        number = (payload.wo_number or "").strip().upper() or f"WO-{uuid.uuid4().hex[:8].upper()}"
        if self.repo.get_order_by_number(org_id, number):
            raise HTTPException(status_code=409, detail="Work order number already exists")
        now = _utcnow()
        row = WorkOrder(
            organization_id=org_id,
            work_package_id=package.id,
            wo_number=number,
            aircraft_id=package.aircraft_id,
            ata_chapter_id=payload.ata_chapter_id,
            title=payload.title.strip(),
            description=(payload.description or "").strip(),
            status="open",
            priority=priority,
            planner_employee_id=payload.planner_employee_id or package.planner_employee_id,
            supervisor_employee_id=payload.supervisor_employee_id or package.supervisor_employee_id,
            publication_id=publication_id,
            publication_revision_id=publication_revision_id,
            due_date=payload.due_date,
            estimated_hours=payload.estimated_hours or Decimal("0.00"),
            actual_hours=Decimal("0.00"),
            version=1,
            created_at=now,
            updated_at=now,
        )
        if package.status == "draft":
            package.status = "planned"
            package.version = int(package.version or 1) + 1
            package.updated_at = now
        self.repo.add_order(row)
        self._commit_or_conflict(detail="Work order conflict")
        self.repo.refresh(row)
        event_framework.publish_sync(
            "work_order.created",
            {"id": row.id, "wo_number": row.wo_number, "aircraft_id": row.aircraft_id},
            organization_id=org_id,
            source="work_orders",
            actor=username,
        )
        return self.order_out(row)

    def get_order(self, order_id: str, *, username: str, session_role: str) -> WorkOrderOut:
        return self.order_out(self._get_org_order(order_id, username=username, session_role=session_role))

    # --- job cards ---
    def list_job_cards(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[JobCardOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        rows = self.repo.list_job_cards(
            organization_id=org_id,
            work_order_id=filters.get("work_order_id"),
            technician_employee_id=filters.get("technician_employee_id"),
            status=filters.get("status"),
            aircraft_id=filters.get("aircraft_id"),
            limit=int(filters.get("limit") or 100),
            offset=int(filters.get("offset") or 0),
        )
        return [self.job_card_out(r) for r in rows]

    def create_job_card(
        self,
        payload: JobCardCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> JobCardOut:
        order = self._get_org_order(
            payload.work_order_id, username=username, session_role=session_role, for_update=True
        )
        org_id = order.organization_id
        priority = (payload.priority or "normal").strip().lower()
        if priority not in PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid priority")
        self._employee_in_org(payload.technician_employee_id, org_id)
        publication_id = payload.publication_id or order.publication_id
        publication_revision_id = payload.publication_revision_id or order.publication_revision_id
        number = (payload.job_card_number or "").strip().upper() or f"JC-{uuid.uuid4().hex[:8].upper()}"
        if self.repo.get_job_card_by_number(org_id, number):
            raise HTTPException(status_code=409, detail="Job card number already exists")

        # Create linked MaintenanceTask — single certify/logbook engine (no duplication).
        task_out = self.maintenance.create_task(
            TaskCreate(
                organization_id=org_id,
                task_number=f"MT-{number}",
                task_type="corrective",
                aircraft_id=order.aircraft_id,
                ata_chapter_id=payload.ata_chapter_id or order.ata_chapter_id,
                title=payload.title.strip(),
                description=(payload.description or "").strip(),
                priority=priority,
                estimated_hours=payload.estimated_hours or Decimal("0.00"),
                publication_id=publication_id,
                publication_revision_id=publication_revision_id,
                component_id=payload.component_id,
                required_parts=payload.required_parts or "",
                required_tools=payload.required_tools or "",
                required_skills=payload.required_skills or "",
                required_certification=payload.required_certification or "",
                independent_inspection_required=payload.independent_inspection_required,
                aca_required=payload.aca_required,
                critical_policy_id=payload.critical_policy_id,
                status="assigned" if payload.technician_employee_id else "open",
                assigned_to_employee_id=payload.technician_employee_id,
            ),
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
        )

        now = _utcnow()
        status_value = "assigned" if payload.technician_employee_id else "draft"
        row = JobCard(
            organization_id=org_id,
            work_order_id=order.id,
            job_card_number=number,
            maintenance_task_id=task_out.id,
            aircraft_id=order.aircraft_id,
            ata_chapter_id=payload.ata_chapter_id or order.ata_chapter_id,
            title=payload.title.strip(),
            description=(payload.description or "").strip(),
            status=status_value,
            priority=priority,
            publication_id=publication_id,
            publication_revision_id=publication_revision_id or task_out.publication_revision_id,
            component_id=payload.component_id,
            required_parts=(payload.required_parts or "").strip(),
            required_tools=(payload.required_tools or "").strip(),
            required_skills=(payload.required_skills or "").strip(),
            required_certification=(payload.required_certification or "").strip(),
            estimated_hours=payload.estimated_hours or Decimal("0.00"),
            actual_hours=Decimal("0.00"),
            technician_employee_id=payload.technician_employee_id,
            hangar_bay=(payload.hangar_bay or "").strip(),
            independent_inspection_required=_flag(payload.independent_inspection_required),
            aca_required=_flag(payload.aca_required),
            version=1,
            created_at=now,
            updated_at=now,
        )
        if order.status in {"draft", "open"}:
            order.status = "in_progress"
            order.version = int(order.version or 1) + 1
            order.updated_at = now
        package = self.repo.get_package(order.work_package_id)
        if package and package.status in {"draft", "planned"}:
            package.status = "in_progress"
            package.actual_start = package.actual_start or now
            package.version = int(package.version or 1) + 1
            package.updated_at = now
        self.repo.add_job_card(row)
        self._commit_or_conflict(detail="Job card conflict")
        self.repo.refresh(row)
        return self.job_card_out(row)

    def get_job_card(self, job_card_id: str, *, username: str, session_role: str) -> JobCardOut:
        return self.job_card_out(self._get_org_card(job_card_id, username=username, session_role=session_role))

    def assign_job_card(
        self,
        job_card_id: str,
        payload: JobCardAssignRequest,
        *,
        username: str,
        session_role: str,
    ) -> JobCardOut:
        card = self._get_org_card(job_card_id, username=username, session_role=session_role, for_update=True)
        if payload.expected_version is not None and int(card.version or 1) != payload.expected_version:
            raise HTTPException(status_code=409, detail="Job card version conflict")
        if card.status in TERMINAL_MUTATION_BLOCK | {"waiting_inspection", "completed"}:
            raise HTTPException(status_code=409, detail=f"Cannot assign from status '{card.status}'")
        if card.status not in {"draft", "assigned", "rejected"}:
            raise HTTPException(status_code=409, detail=f"Cannot assign from status '{card.status}'")
        self._employee_in_org(payload.technician_employee_id, card.organization_id)
        # Concurrency: only one active assignee; reassign replaces under row lock.
        card.technician_employee_id = payload.technician_employee_id
        if payload.hangar_bay:
            card.hangar_bay = payload.hangar_bay.strip()
        if payload.notes:
            card.notes = ((card.notes or "") + "\n" + payload.notes.strip()).strip()
        card.status = "assigned"
        card.version = int(card.version or 1) + 1
        card.updated_at = _utcnow()
        if card.maintenance_task_id:
            task = self.maintenance.repo.get_task(card.maintenance_task_id, for_update=True)
            if task and task.status in {"open", "assigned"}:
                task.assigned_to_employee_id = payload.technician_employee_id
                task.status = "assigned"
                task.version = int(task.version or 1) + 1
                task.updated_at = card.updated_at
        self._commit_or_conflict(detail="Job card assign conflict")
        self.repo.refresh(card)
        return self.job_card_out(card)

    def transition_job_card(
        self,
        job_card_id: str,
        payload: JobCardTransitionRequest,
        *,
        username: str,
        session_role: str,
    ) -> JobCardOut:
        card = self._get_org_card(job_card_id, username=username, session_role=session_role, for_update=True)
        if payload.expected_version is not None and int(card.version or 1) != payload.expected_version:
            raise HTTPException(status_code=409, detail="Job card version conflict")
        current = card.status
        target = payload.to_status.strip().lower()
        if target not in JC_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid job card status")
        if target in CERT_GATED_STATUSES:
            raise HTTPException(
                status_code=409,
                detail="Certification-gated status requires complete-work, inspect, or release endpoint",
            )
        if current == "released" and target == "closed":
            if not has_permissions(session_role, ("work_order.manage",)) and not has_permissions(
                session_role, ("maintenance.manage",)
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Supervisor/planner authority required to close released work",
                )
        # Transitions come from the generic workflow engine (Program A / AEOS), not a module-local map.
        from ..platform.workflow_bridge import JOB_CARD_WORKFLOW_CODE, WorkflowBridge
        from ..shared import ActorContext

        bridge = WorkflowBridge(self.db)
        bridge.ensure_job_card_definition(card.organization_id)
        bridge.assert_transition(card.organization_id, JOB_CARD_WORKFLOW_CODE, current, target)
        if target == "accepted":
            if not card.technician_employee_id:
                raise HTTPException(status_code=409, detail="Job card has no assigned technician")
            # Prevent double-accept races: only assigned → accepted under row lock.
            if current != "assigned":
                raise HTTPException(status_code=409, detail=f"Invalid transition from '{current}' to '{target}'")
        if target == "assigned" and payload.technician_employee_id:
            self._employee_in_org(payload.technician_employee_id, card.organization_id)
            card.technician_employee_id = payload.technician_employee_id
        if payload.actual_hours is not None:
            if current in TERMINAL_MUTATION_BLOCK:
                raise HTTPException(status_code=409, detail="Cannot change hours on released/closed work")
            card.actual_hours = payload.actual_hours
            self._rollup_hours(card)
        if payload.notes:
            if current in TERMINAL_MUTATION_BLOCK and target != "closed":
                raise HTTPException(status_code=409, detail="Cannot change notes on released/closed work")
            card.notes = ((card.notes or "") + "\n" + payload.notes.strip()).strip()
        card.status = target
        card.version = int(card.version or 1) + 1
        card.updated_at = _utcnow()
        self._sync_order_package_status(card)
        self._commit_or_conflict(detail="Job card transition conflict")
        self.repo.refresh(card)
        actor = ActorContext(
            username=username,
            role=session_role,
            organization_id=card.organization_id,
            site_id="",
        )
        bridge.sync_instance(
            actor,
            organization_id=card.organization_id,
            definition_code=JOB_CARD_WORKFLOW_CODE,
            entity_type="job_card",
            entity_id=card.id,
            to_state=target,
            comment=payload.notes or "",
        )
        return self.job_card_out(card)

    def _rollup_hours(self, card: JobCard) -> None:
        order = self.repo.get_order(card.work_order_id, for_update=True)
        if order is None:
            return
        cards = self.repo.list_job_cards(organization_id=card.organization_id, work_order_id=order.id, limit=500)
        order.actual_hours = sum((Decimal(str(c.actual_hours or 0)) for c in cards), Decimal("0.00"))
        order.updated_at = _utcnow()
        package = self.repo.get_package(order.work_package_id, for_update=True)
        if package is None:
            return
        orders = self.repo.list_orders(organization_id=card.organization_id, work_package_id=package.id, limit=500)
        package.actual_hours = sum((Decimal(str(o.actual_hours or 0)) for o in orders), Decimal("0.00"))
        package.updated_at = _utcnow()

    def _sync_order_package_status(self, card: JobCard) -> None:
        order = self.repo.get_order(card.work_order_id, for_update=True)
        if order is None:
            return
        cards = self.repo.list_job_cards(organization_id=card.organization_id, work_order_id=order.id, limit=500)
        statuses = {c.status for c in cards}
        if statuses and statuses <= {"closed", "released"}:
            order.status = "released" if "released" in statuses else "closed"
        elif "rejected" in statuses:
            order.status = "delayed"
        elif statuses & {"in_progress", "paused", "waiting_parts", "waiting_engineering", "waiting_inspection", "completed"}:
            order.status = "in_progress"
        order.version = int(order.version or 1) + 1
        order.updated_at = _utcnow()
        package = self.repo.get_package(order.work_package_id, for_update=True)
        if package is None:
            return
        orders = self.repo.list_orders(organization_id=card.organization_id, work_package_id=package.id, limit=500)
        o_statuses = {o.status for o in orders}
        if o_statuses and o_statuses <= {"closed", "released"}:
            package.status = "released" if "released" in o_statuses else "closed"
            package.actual_finish = package.actual_finish or _utcnow()
        elif "delayed" in o_statuses or "in_progress" in o_statuses:
            package.status = "in_progress"
            package.actual_start = package.actual_start or _utcnow()
        package.version = int(package.version or 1) + 1
        package.updated_at = _utcnow()

    def add_attachment(
        self,
        job_card_id: str,
        payload: JobCardAttachmentCreate,
        *,
        username: str,
        session_role: str,
    ) -> JobCardAttachmentOut:
        card = self._get_org_card(job_card_id, username=username, session_role=session_role, for_update=True)
        if card.status in TERMINAL_MUTATION_BLOCK:
            raise HTTPException(status_code=409, detail="Cannot attach files to released or closed job cards")
        row = JobCardAttachment(
            organization_id=card.organization_id,
            job_card_id=card.id,
            kind=payload.kind,
            title=(payload.title or "").strip(),
            storage_uri=(payload.storage_uri or "").strip(),
            content_type=(payload.content_type or "").strip(),
            notes=(payload.notes or "").strip(),
            created_by=username,
            created_at=_utcnow(),
        )
        self.repo.add_attachment(row)
        self._commit_or_conflict(detail="Attachment conflict")
        self.repo.refresh(row)
        return self.attachment_out(row)

    def list_attachments(self, job_card_id: str, *, username: str, session_role: str) -> list[JobCardAttachmentOut]:
        self._get_org_card(job_card_id, username=username, session_role=session_role)
        return [self.attachment_out(r) for r in self.repo.list_attachments(job_card_id)]

    def inspect_job_card(
        self,
        job_card_id: str,
        payload: JobCardInspectRequest,
        *,
        username: str,
        session_role: str,
    ) -> JobCardOut:
        card = self._get_org_card(job_card_id, username=username, session_role=session_role, for_update=True)
        if not card.maintenance_task_id:
            raise HTTPException(status_code=409, detail="Job card has no linked maintenance task")
        if card.status in TERMINAL_MUTATION_BLOCK:
            raise HTTPException(status_code=409, detail="Released/closed job cards cannot be inspected")

        if payload.decision == "independent_inspection":
            if card.status != "completed":
                raise HTTPException(
                    status_code=409,
                    detail="Independent inspection requires prior inspection approval (completed)",
                )
        elif card.status != "waiting_inspection":
            raise HTTPException(status_code=409, detail="Job card must be waiting_inspection for QA decisions")

        if payload.decision == "reject":
            card.status = "rejected"
            card.rework_reason = payload.notes or "Rejected by inspector"
            card.inspector_employee_id = payload.employee_id
            card.version = int(card.version or 1) + 1
            card.updated_at = _utcnow()
            self._sync_order_package_status(card)
            self._commit_or_conflict(detail="Inspect reject conflict")
            self.repo.refresh(card)
            return self.job_card_out(card)

        if payload.decision == "rework":
            card.status = "in_progress"
            card.rework_reason = payload.notes or "Rework required"
            card.inspector_employee_id = payload.employee_id
            card.version = int(card.version or 1) + 1
            card.updated_at = _utcnow()
            self._sync_order_package_status(card)
            self._commit_or_conflict(detail="Inspect rework conflict")
            self.repo.refresh(card)
            return self.job_card_out(card)

        step = "independent_inspection" if payload.decision == "independent_inspection" else "inspected"
        events = self.maintenance.repo.list_certification_events(card.maintenance_task_id)
        done = {e.step for e in events}
        if "performed" not in done:
            raise HTTPException(
                status_code=409,
                detail="Technician must complete work (performed) before inspection",
            )
        if step in done:
            raise HTTPException(status_code=409, detail=f"Step already completed: {step}")
        self.maintenance.sign_action(
            card.maintenance_task_id,
            CertifyRequest(
                step=step,
                employee_id=payload.employee_id,
                method=payload.method,
                credential=payload.credential,
                notes=payload.notes,
                actual_hours=payload.actual_hours,
            ),
            username=username,
            session_role=session_role,
        )
        card = self._get_org_card(job_card_id, username=username, session_role=session_role, for_update=True)
        if step == "independent_inspection":
            card.independent_inspector_employee_id = payload.employee_id
        else:
            card.inspector_employee_id = payload.employee_id
        card.status = "completed"
        if payload.actual_hours is not None:
            card.actual_hours = payload.actual_hours
            self._rollup_hours(card)
        card.version = int(card.version or 1) + 1
        card.updated_at = _utcnow()
        self._sync_order_package_status(card)
        self._commit_or_conflict(detail="Inspect approve conflict")
        self.repo.refresh(card)
        return self.job_card_out(card)

    def complete_job_card_work(
        self,
        job_card_id: str,
        *,
        employee_id: str,
        method: str,
        credential: str | None,
        notes: str = "",
        actual_hours: Decimal | None = None,
        username: str,
        session_role: str,
    ) -> JobCardOut:
        """Technician completion: sign performed + move card to waiting_inspection."""
        card = self._get_org_card(job_card_id, username=username, session_role=session_role, for_update=True)
        if not card.maintenance_task_id:
            raise HTTPException(status_code=409, detail="Job card has no linked maintenance task")
        if card.status not in {"accepted", "in_progress", "paused", "assigned"}:
            raise HTTPException(status_code=409, detail="Job card is not in an executable state")
        self.maintenance.sign_action(
            card.maintenance_task_id,
            CertifyRequest(
                step="performed",
                employee_id=employee_id,
                method=method,
                credential=credential,
                notes=notes or f"Completed job card {card.job_card_number}",
                actual_hours=actual_hours,
            ),
            username=username,
            session_role=session_role,
        )
        card = self._get_org_card(job_card_id, username=username, session_role=session_role, for_update=True)
        card.status = "waiting_inspection"
        card.technician_employee_id = employee_id
        if actual_hours is not None:
            card.actual_hours = actual_hours
            self._rollup_hours(card)
        if notes:
            card.notes = ((card.notes or "") + "\n" + notes.strip()).strip()
        card.version = int(card.version or 1) + 1
        card.updated_at = _utcnow()
        self._sync_order_package_status(card)
        self._commit_or_conflict(detail="Complete work conflict")
        self.repo.refresh(card)
        return self.job_card_out(card)

    def release_job_card(
        self,
        job_card_id: str,
        payload: JobCardReleaseRequest,
        *,
        username: str,
        session_role: str,
    ) -> JobCardOut:
        card = self._get_org_card(job_card_id, username=username, session_role=session_role, for_update=True)
        if not card.maintenance_task_id:
            raise HTTPException(status_code=409, detail="Job card has no linked maintenance task")
        if card.status == "released":
            raise HTTPException(status_code=409, detail="Job card already released")
        if card.status != "completed":
            raise HTTPException(status_code=409, detail="Job card must be inspection-completed before ACA release")
        if not card.publication_id or not card.publication_revision_id:
            raise HTTPException(
                status_code=409,
                detail="Job card must reference an immutable publication revision before ACA release",
            )
        if not card.ata_chapter_id:
            raise HTTPException(status_code=409, detail="Job card ATA chapter required before ACA release")
        rev = self.publications.get_revision(card.publication_revision_id)
        if rev is None or rev.publication_id != card.publication_id:
            raise HTTPException(status_code=409, detail="Publication revision not found for job card")
        pub = self.publications.get_publication(card.publication_id)
        if pub is None or pub.status == "archived":
            raise HTTPException(status_code=409, detail="Publication is archived or missing")

        events = self.maintenance.repo.list_certification_events(card.maintenance_task_id)
        done = {e.step for e in events}
        if "aircraft_released" in done:
            raise HTTPException(status_code=409, detail="Aircraft already released for linked task")
        for required in ("performed", "inspected"):
            if required not in done:
                raise HTTPException(status_code=409, detail=f"Missing certification step before release: {required}")
        if _truthy(card.independent_inspection_required) and "independent_inspection" not in done:
            raise HTTPException(status_code=409, detail="Independent inspection required before release")

        release_snapshot = (
            f"job_card:{card.job_card_number};publication={card.publication_id};"
            f"revision={card.publication_revision_id};revision_number={rev.revision_number};"
            f"revision_date={(rev.revision_date.isoformat() if rev.revision_date else '')};"
            f"effective_date={(rev.effective_date.isoformat() if rev.effective_date else '')};"
            f"ata={card.ata_chapter_id};required_certification={card.required_certification or ''};"
            f"required_skills={card.required_skills or ''}"
        )

        if _truthy(card.aca_required) and "aca_certified" not in done:
            self.maintenance.sign_action(
                card.maintenance_task_id,
                CertifyRequest(
                    step="aca_certified",
                    employee_id=payload.employee_id,
                    method=payload.method,
                    credential=payload.credential,
                    notes=release_snapshot,
                ),
                username=username,
                session_role=session_role,
            )
        self.maintenance.sign_action(
            card.maintenance_task_id,
            CertifyRequest(
                step="aircraft_released",
                employee_id=payload.employee_id,
                method=payload.method,
                credential=payload.credential,
                notes=(payload.notes or f"Released job card {card.job_card_number}") + ";" + release_snapshot,
                actual_hours=payload.actual_hours,
            ),
            username=username,
            session_role=session_role,
        )

        card = self._get_org_card(job_card_id, username=username, session_role=session_role, for_update=True)
        card.status = "released"
        card.aca_employee_id = payload.employee_id
        if payload.actual_hours is not None:
            card.actual_hours = payload.actual_hours
            self._rollup_hours(card)
        card.version = int(card.version or 1) + 1
        card.updated_at = _utcnow()
        self._sync_order_package_status(card)
        self._commit_or_conflict(detail="Release conflict")
        self.repo.refresh(card)
        return self.job_card_out(card)

    def dashboard(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
        technician_employee_id: str | None = None,
        role: str = "manager",
    ) -> ExecutionDashboardOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        by_status = self.repo.count_job_cards_by_status(org_id)
        open_wo = self.repo.count_orders_by_status(org_id, "open") + self.repo.count_orders_by_status(
            org_id, "in_progress"
        )
        delayed = self.repo.count_orders_by_status(org_id, "delayed")
        my_assigned = 0
        if technician_employee_id:
            my_assigned = len(
                self.repo.list_job_cards(
                    organization_id=org_id,
                    technician_employee_id=technician_employee_id,
                    limit=500,
                )
            )
        return ExecutionDashboardOut(
            role=role,
            open_work_orders=open_wo,
            delayed_work_orders=delayed,
            job_cards_by_status=by_status,
            my_assigned_job_cards=my_assigned,
            awaiting_inspection=by_status.get("waiting_inspection", 0),
            awaiting_release=by_status.get("completed", 0),
            released_today=by_status.get("released", 0),
        )

    def report(
        self,
        report: str,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
    ) -> ReportSummaryOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        report_key = report.strip().lower()
        rows: list[dict] = []
        if report_key == "open_work_orders":
            for o in self.repo.list_orders(organization_id=org_id, status="open", limit=500):
                rows.append(self.order_out(o).model_dump(mode="json"))
            for o in self.repo.list_orders(organization_id=org_id, status="in_progress", limit=500):
                rows.append(self.order_out(o).model_dump(mode="json"))
        elif report_key == "delayed_work_orders":
            for o in self.repo.list_orders(organization_id=org_id, status="delayed", limit=500):
                rows.append(self.order_out(o).model_dump(mode="json"))
        elif report_key == "labor_hours":
            for c in self.repo.list_job_cards(organization_id=org_id, limit=500):
                rows.append(
                    {
                        "job_card_number": c.job_card_number,
                        "estimated_hours": str(c.estimated_hours or 0),
                        "actual_hours": str(c.actual_hours or 0),
                        "technician_employee_id": c.technician_employee_id,
                        "status": c.status,
                    }
                )
        elif report_key == "inspection_status":
            for c in self.repo.list_job_cards(organization_id=org_id, status="waiting_inspection", limit=500):
                rows.append(self.job_card_out(c).model_dump(mode="json"))
        elif report_key == "release_status":
            for c in self.repo.list_job_cards(organization_id=org_id, status="released", limit=500):
                rows.append(self.job_card_out(c).model_dump(mode="json"))
            for c in self.repo.list_job_cards(organization_id=org_id, status="completed", limit=500):
                rows.append(self.job_card_out(c).model_dump(mode="json"))
        elif report_key == "technician_productivity":
            tally: dict[str, dict[str, Decimal | int]] = {}
            for c in self.repo.list_job_cards(organization_id=org_id, limit=500):
                key = c.technician_employee_id or "unassigned"
                bucket = tally.setdefault(key, {"cards": 0, "actual_hours": Decimal("0.00")})
                bucket["cards"] = int(bucket["cards"]) + 1
                bucket["actual_hours"] = Decimal(str(bucket["actual_hours"])) + Decimal(str(c.actual_hours or 0))
            rows = [
                {"technician_employee_id": k, "cards": int(v["cards"]), "actual_hours": str(v["actual_hours"])}
                for k, v in tally.items()
            ]
        elif report_key == "aircraft_status":
            packages = self.repo.list_packages(organization_id=org_id, limit=500)
            for p in packages:
                rows.append(
                    {
                        "aircraft_id": p.aircraft_id,
                        "registration": p.registration,
                        "package_number": p.package_number,
                        "status": p.status,
                        "hangar_bay": p.hangar_bay,
                    }
                )
        else:
            raise HTTPException(status_code=400, detail="Unknown report type")
        return ReportSummaryOut(report=report_key, organization_id=org_id, generated_at=_utcnow(), rows=rows)
