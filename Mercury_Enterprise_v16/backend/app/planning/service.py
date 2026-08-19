"""Sprint 9 planning service — programs, MPD, forecast, due list, WP generation."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..fleet.repository import FleetRepository
from ..org.service import OrganizationService
from ..work_orders.schemas import JobCardCreate, WorkOrderCreate, WorkPackageCreate
from ..work_orders.service import WorkOrderService
from .models import (
    AirworthinessDirective,
    AircraftUtilization,
    DeferredDefect,
    EngineeringOrder,
    HangarPlan,
    MaintenanceCheck,
    MaintenanceProgram,
    MaintenanceProgramRevision,
    MelItem,
    MpdTask,
    PartsPlanLine,
    ServiceBulletin,
    ToolPlanLine,
    WorkforcePlanLine,
)
from .repository import PlanningRepository
from .schemas import (
    AdCreate,
    AdOut,
    AircraftStatusOut,
    CheckCreate,
    CheckOut,
    DefectCreate,
    DefectOut,
    DueListOut,
    EoCreate,
    EoOut,
    ForecastItemOut,
    ForecastOut,
    GeneratePackageOut,
    GeneratePackageRequest,
    HangarPlanCreate,
    HangarPlanOut,
    MelItemCreate,
    MelItemOut,
    MpdTaskCreate,
    MpdTaskOut,
    PlannerDashboardOut,
    ProgramCreate,
    ProgramOut,
    ProgramRevisionCreate,
    ProgramRevisionOut,
    SbCreate,
    SbOut,
    UtilizationOut,
    UtilizationUpsert,
    WorkforcePlanLineCreate,
    WorkforcePlanLineOut,
    WorkforcePlanLineUpdate,
)

logger = logging.getLogger("mercury.planning")

CHECK_TYPES = frozenset(
    {
        "preflight",
        "transit",
        "daily",
        "weekly",
        "service",
        "a",
        "b",
        "c",
        "d",
        "structural",
        "engine",
        "landing_gear",
        "special",
        "custom",
    }
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _truthy(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in {"1", "true", "yes", "on"}


class PlanningService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PlanningRepository(db)
        self.org = OrganizationService(db)
        self.fleet = FleetRepository(db)
        self.work_orders = WorkOrderService(db)

    def ensure_seed_data(self) -> None:
        org_id = "org-aviation-east"
        if self.org.repo.get_organization(org_id) is None:
            return
        if self.repo.get_program_by_code(org_id, "MP-A320-LINE") is not None:
            self._ensure_demo_workforce_lines(org_id)
            return
        now = _utcnow()
        program = MaintenanceProgram(
            id="mp-a320-line",
            organization_id=org_id,
            program_code="MP-A320-LINE",
            title="A320 Family Line Maintenance Program",
            manufacturer="Airbus",
            aircraft_family="A320",
            aircraft_model_id="model-a320",
            operator_name="Aviation East",
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_program(program)
        self.repo.flush()
        rev = MaintenanceProgramRevision(
            id="mpr-a320-line-1",
            organization_id=org_id,
            program_id=program.id,
            revision_number="1",
            effective_date=now - timedelta(days=30),
            approval_authority="Transport Canada",
            approval_reference="MP-APP-001",
            status="active",
            notes="Demo program revision",
            created_at=now,
        )
        self.repo.add_revision(rev)
        program.current_revision_id = rev.id
        self.repo.flush()
        self.repo.add_mpd_task(
            MpdTask(
                id="mpd-a320-21-daily",
                organization_id=org_id,
                program_revision_id=rev.id,
                task_number="MPD-21-00-00-001",
                title="Daily cabin pressure system inspection",
                ata_chapter_id="ata-21-00",
                description="Visual and functional check per MPD",
                required_skill="Airframe",
                estimated_manhours=Decimal("1.50"),
                interval_calendar_days=1,
                interval_flight_hours=Decimal("25.00"),
                repeat_policy="repeat",
                required_publications="AMM 21-00",
                required_tools="Standard toolkit",
                required_parts="",
                required_certifications="AME",
                required_inspection=_flag(True),
                required_ii=_flag(False),
                required_aca=_flag(True),
                applicability="A320 family",
                status="active",
                revision_label="1",
                created_at=now,
                updated_at=now,
            )
        )
        self.repo.add_mpd_task(
            MpdTask(
                id="mpd-a320-a-check",
                organization_id=org_id,
                program_revision_id=rev.id,
                task_number="MPD-05-00-00-A",
                title="A-Check zone inspection package",
                ata_chapter_id="ata-05-00",
                description="A-check structural/systems package",
                required_skill="Airframe",
                estimated_manhours=Decimal("24.00"),
                interval_calendar_days=60,
                interval_flight_hours=Decimal("600.00"),
                interval_flight_cycles=400,
                repeat_policy="repeat",
                required_publications="MPD; AMM",
                required_tools="Torque set; Borescope",
                required_parts="Consumables kit",
                required_certifications="AME",
                required_inspection=_flag(True),
                required_ii=_flag(True),
                required_aca=_flag(True),
                applicability="A320ceo",
                status="active",
                revision_label="1",
                created_at=now,
                updated_at=now,
            )
        )
        util = AircraftUtilization(
            id="util-ac-c-gmea",
            organization_id=org_id,
            aircraft_id="ac-c-gmea",
            location="YUL Hangar 1",
            ops_status="available",
            flight_hours=Decimal("12500.00"),
            flight_cycles=8200,
            landings=8200,
            engine_hours=Decimal("11800.00"),
            apu_hours=Decimal("2100.00"),
            traffic_light="yellow",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_utilization(util)
        check = MaintenanceCheck(
            id="chk-a320-a-c-gmea",
            organization_id=org_id,
            program_revision_id=rev.id,
            aircraft_id="ac-c-gmea",
            check_code="A-CHK-C-GMEA",
            check_type="a",
            title="A Check — C-GMEA",
            description="Demo A-check due soon",
            interval_calendar_days=60,
            interval_flight_hours=Decimal("600.00"),
            interval_flight_cycles=400,
            estimated_duration_hours=Decimal("36.00"),
            last_done_at=now - timedelta(days=50),
            last_done_hours=Decimal("11950.00"),
            last_done_cycles=7900,
            next_due_at=now + timedelta(days=10),
            next_due_hours=Decimal("12550.00"),
            next_due_cycles=8300,
            status="due",
            hangar="Hangar-1",
            bay="Bay-2",
            shift_code="DAY",
            team_name="Line Team Alpha",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_check(check)
        self.repo.add_ad(
            AirworthinessDirective(
                id="ad-demo-faa-2024",
                organization_id=org_id,
                ad_number="AD-2024-12-01",
                authority="faa",
                manufacturer="Airbus",
                revision="0",
                title="Demo FAA AD — inspection of landing gear pins",
                applicability="A320 family",
                mandatory=_flag(True),
                compliance_status="open",
                due_date=now + timedelta(days=25),
                publication_id="pub-amm-a320-71",
                history_notes="Seeded for Sprint 9",
                created_at=now,
                updated_at=now,
            )
        )
        self.repo.add_sb(
            ServiceBulletin(
                id="sb-demo-airbus-001",
                organization_id=org_id,
                sb_number="SB-A320-32-1234",
                sb_type="sb",
                manufacturer="Airbus",
                revision="1",
                title="NLG door latch improvement",
                applicability="A320ceo",
                priority="recommended",
                compliance_status="open",
                due_date=now + timedelta(days=90),
                history_notes="Seeded",
                created_at=now,
                updated_at=now,
            )
        )
        self.repo.add_eo(
            EngineeringOrder(
                id="eo-demo-001",
                organization_id=org_id,
                eo_number="EO-EAST-1001",
                revision="0",
                title="Install revised bonding jumper",
                status="approved",
                effectivity="C-GMEA",
                work_instructions="Remove/install bonding jumper per SRM",
                references="SRM 51-00; AMM 20-00",
                due_date=now + timedelta(days=45),
                approved_by="Engineering",
                approved_at=now,
                history_notes="Seeded",
                created_at=now,
                updated_at=now,
            )
        )
        mel = MelItem(
            id="mel-21-01",
            organization_id=org_id,
            list_type="mel",
            item_number="21-01",
            title="Pack flow control valve",
            ata_chapter_id="ata-21-00",
            dispatch_category="C",
            repair_interval_days=10,
            dispatch_restrictions="No icing conditions",
            aircraft_model_id="model-a320",
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_mel(mel)
        self.repo.add_defect(
            DeferredDefect(
                id="dd-demo-001",
                organization_id=org_id,
                aircraft_id="ac-c-gmea",
                defect_number="DD-1001",
                title="Pack flow control sluggish",
                description="Deferred under MEL 21-01",
                status="deferred",
                deferral_type="mel",
                mel_item_id=mel.id,
                dispatch_category="C",
                repair_interval_days=10,
                expires_at=now + timedelta(days=7),
                ata_chapter_id="ata-21-00",
                alert_level="yellow",
                created_at=now,
                updated_at=now,
            )
        )
        self.repo.commit()
        self._ensure_demo_workforce_lines(org_id)

    def _commit_or_conflict(self, *, detail: str) -> None:
        try:
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail=detail) from exc

    def _apply_logistics_planning(
        self, *, organization_id: str, work_package_id: str, username: str
    ) -> None:
        """Bridge Sprint 9 plan lines to Program B logistics reserve / tool assign."""
        from ..logistics.service import LogisticsService

        logistics = LogisticsService(self.db)
        parts_lines = self.repo.list_parts_lines(organization_id, work_package_id)
        if parts_lines:
            result = logistics.run_material_planning(
                organization_id,
                work_package_id,
                [
                    {
                        "id": line.id,
                        "part_number": line.part_number,
                        "qty_required": line.qty_required,
                    }
                    for line in parts_lines
                ],
                username=username,
                auto_purchase_request=True,
            )
            by_id = {line.parts_plan_line_id: line for line in result.lines}
            for plan_line in parts_lines:
                update = by_id.get(plan_line.id)
                if update is None:
                    continue
                plan_line.qty_available = int(update.qty_available)
                plan_line.qty_reserved = int(update.qty_reserved)
                plan_line.status = update.status
                if update.expected_delivery is not None:
                    plan_line.expected_delivery = update.expected_delivery

        tool_lines = self.repo.list_tool_lines(organization_id, work_package_id)
        if tool_lines:
            tool_result = logistics.run_tool_planning(
                organization_id,
                work_package_id,
                [
                    {
                        "id": line.id,
                        "tool_code": line.tool_code,
                    }
                    for line in tool_lines
                ],
                username=username,
            )
            by_tool = {line.tool_plan_line_id: line for line in tool_result.lines}
            for plan_line in tool_lines:
                update = by_tool.get(plan_line.id)
                if update is None:
                    continue
                plan_line.status = update.status
                plan_line.calibration_status = update.calibration_status
                if update.calibration_expires_at is not None:
                    plan_line.calibration_expires_at = update.calibration_expires_at

    def resolve_org_id(
        self, *, username: str, session_role: str, session_org_id: str, requested_org_id: str | None
    ) -> str:
        org_id = (requested_org_id or session_org_id).strip()
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=org_id)
        return org_id

    def assert_org_access(self, *, username: str, session_role: str, organization_id: str) -> None:
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=organization_id)

    def _require_live(self, row, *, username: str, session_role: str, not_found: str):
        if row is None or getattr(row, "deleted_at", None) is not None:
            raise HTTPException(status_code=404, detail=not_found)
        self.assert_org_access(username=username, session_role=session_role, organization_id=row.organization_id)
        return row

    # --- serializers ---
    @staticmethod
    def program_out(row: MaintenanceProgram) -> ProgramOut:
        return ProgramOut(
            id=row.id,
            organization_id=row.organization_id,
            program_code=row.program_code,
            title=row.title,
            manufacturer=row.manufacturer or "",
            aircraft_family=row.aircraft_family or "",
            aircraft_model_id=row.aircraft_model_id,
            operator_name=row.operator_name or "",
            status=row.status,
            current_revision_id=row.current_revision_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def revision_out(row: MaintenanceProgramRevision) -> ProgramRevisionOut:
        return ProgramRevisionOut(
            id=row.id,
            organization_id=row.organization_id,
            program_id=row.program_id,
            revision_number=row.revision_number,
            effective_date=row.effective_date,
            approval_authority=row.approval_authority or "",
            approval_reference=row.approval_reference or "",
            status=row.status,
            notes=row.notes or "",
            created_at=row.created_at,
        )

    @staticmethod
    def mpd_out(row: MpdTask) -> MpdTaskOut:
        return MpdTaskOut(
            id=row.id,
            organization_id=row.organization_id,
            program_revision_id=row.program_revision_id,
            task_number=row.task_number,
            title=row.title,
            ata_chapter_id=row.ata_chapter_id,
            description=row.description or "",
            required_skill=row.required_skill or "",
            estimated_manhours=Decimal(str(row.estimated_manhours or 0)),
            interval_calendar_days=row.interval_calendar_days,
            interval_flight_hours=row.interval_flight_hours,
            interval_flight_cycles=row.interval_flight_cycles,
            interval_landings=row.interval_landings,
            interval_engine_hours=row.interval_engine_hours,
            interval_apu_hours=row.interval_apu_hours,
            interval_component_hours=row.interval_component_hours,
            threshold_flight_hours=row.threshold_flight_hours,
            threshold_flight_cycles=row.threshold_flight_cycles,
            threshold_calendar_days=row.threshold_calendar_days,
            repeat_policy=row.repeat_policy,
            required_publications=row.required_publications or "",
            required_tools=row.required_tools or "",
            required_parts=row.required_parts or "",
            required_certifications=row.required_certifications or "",
            required_inspection=_truthy(row.required_inspection),
            required_ii=_truthy(row.required_ii),
            required_aca=_truthy(row.required_aca),
            applicability=row.applicability or "",
            status=row.status,
            revision_label=row.revision_label or "",
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def check_out(row: MaintenanceCheck) -> CheckOut:
        return CheckOut(
            id=row.id,
            organization_id=row.organization_id,
            program_revision_id=row.program_revision_id,
            aircraft_id=row.aircraft_id,
            check_code=row.check_code,
            check_type=row.check_type,
            title=row.title or "",
            description=row.description or "",
            interval_calendar_days=row.interval_calendar_days,
            interval_flight_hours=row.interval_flight_hours,
            interval_flight_cycles=row.interval_flight_cycles,
            estimated_duration_hours=Decimal(str(row.estimated_duration_hours or 0)),
            last_done_at=row.last_done_at,
            last_done_hours=row.last_done_hours,
            last_done_cycles=row.last_done_cycles,
            next_due_at=row.next_due_at,
            next_due_hours=row.next_due_hours,
            next_due_cycles=row.next_due_cycles,
            status=row.status,
            generated_work_package_id=row.generated_work_package_id,
            hangar=row.hangar or "",
            bay=row.bay or "",
            shift_code=row.shift_code or "",
            team_name=row.team_name or "",
            supervisor_employee_id=row.supervisor_employee_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    # --- programs ---
    def list_programs(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[ProgramOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        return [
            self.program_out(r)
            for r in self.repo.list_programs(
                organization_id=org_id, limit=int(filters.get("limit") or 100), offset=int(filters.get("offset") or 0)
            )
        ]

    def create_program(
        self, payload: ProgramCreate, *, username: str, session_role: str, session_org_id: str
    ) -> ProgramOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        code = payload.program_code.strip().upper()
        if self.repo.get_program_by_code(org_id, code):
            raise HTTPException(status_code=409, detail="Program code already exists")
        now = _utcnow()
        program = MaintenanceProgram(
            organization_id=org_id,
            program_code=code,
            title=payload.title.strip(),
            manufacturer=(payload.manufacturer or "").strip(),
            aircraft_family=(payload.aircraft_family or "").strip(),
            aircraft_model_id=payload.aircraft_model_id,
            operator_name=(payload.operator_name or "").strip(),
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_program(program)
        self.repo.flush()
        rev = MaintenanceProgramRevision(
            organization_id=org_id,
            program_id=program.id,
            revision_number=(payload.revision_number or "1").strip(),
            effective_date=payload.effective_date or now,
            approval_authority=(payload.approval_authority or "").strip(),
            approval_reference=(payload.approval_reference or "").strip(),
            status="active",
            created_at=now,
        )
        self.repo.add_revision(rev)
        self.repo.flush()
        program.current_revision_id = rev.id
        self._commit_or_conflict(detail="Program conflict")
        self.repo.refresh(program)
        return self.program_out(program)

    def add_program_revision(
        self,
        program_id: str,
        payload: ProgramRevisionCreate,
        *,
        username: str,
        session_role: str,
    ) -> ProgramRevisionOut:
        program = self.repo.get_program(program_id, for_update=True)
        if program is None or program.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Program not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=program.organization_id)
        now = _utcnow()
        # Supersede current active revision — never overwrite.
        if payload.activate and program.current_revision_id:
            current = self.repo.get_revision(program.current_revision_id)
            if current and current.status == "active":
                current.status = "superseded"
        rev = MaintenanceProgramRevision(
            organization_id=program.organization_id,
            program_id=program.id,
            revision_number=payload.revision_number.strip(),
            effective_date=payload.effective_date or now,
            approval_authority=(payload.approval_authority or "").strip(),
            approval_reference=(payload.approval_reference or "").strip(),
            status="active" if payload.activate else "draft",
            notes=(payload.notes or "").strip(),
            created_at=now,
        )
        self.repo.add_revision(rev)
        self.repo.flush()
        if payload.activate:
            program.current_revision_id = rev.id
            program.updated_at = now
        self._commit_or_conflict(detail="Program revision conflict")
        self.repo.refresh(rev)
        return self.revision_out(rev)

    def list_revisions(self, program_id: str, *, username: str, session_role: str) -> list[ProgramRevisionOut]:
        program = self.repo.get_program(program_id)
        if program is None:
            raise HTTPException(status_code=404, detail="Program not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=program.organization_id)
        return [self.revision_out(r) for r in self.repo.list_revisions(program_id)]

    # --- MPD ---
    def list_mpd(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[MpdTaskOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        return [
            self.mpd_out(r)
            for r in self.repo.list_mpd_tasks(
                organization_id=org_id,
                program_revision_id=filters.get("program_revision_id"),
                limit=int(filters.get("limit") or 100),
                offset=int(filters.get("offset") or 0),
            )
        ]

    def create_mpd_task(
        self, payload: MpdTaskCreate, *, username: str, session_role: str, session_org_id: str
    ) -> MpdTaskOut:
        rev = self.repo.get_revision(payload.program_revision_id)
        if rev is None:
            raise HTTPException(status_code=404, detail="Program revision not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=rev.organization_id)
        now = _utcnow()
        row = MpdTask(
            organization_id=rev.organization_id,
            program_revision_id=rev.id,
            task_number=payload.task_number.strip().upper(),
            title=payload.title.strip(),
            ata_chapter_id=payload.ata_chapter_id,
            description=(payload.description or "").strip(),
            required_skill=(payload.required_skill or "").strip(),
            estimated_manhours=payload.estimated_manhours or Decimal("0.00"),
            interval_calendar_days=payload.interval_calendar_days,
            interval_flight_hours=payload.interval_flight_hours,
            interval_flight_cycles=payload.interval_flight_cycles,
            interval_landings=payload.interval_landings,
            interval_engine_hours=payload.interval_engine_hours,
            interval_apu_hours=payload.interval_apu_hours,
            interval_component_hours=payload.interval_component_hours,
            threshold_flight_hours=payload.threshold_flight_hours,
            threshold_flight_cycles=payload.threshold_flight_cycles,
            threshold_calendar_days=payload.threshold_calendar_days,
            repeat_policy=(payload.repeat_policy or "repeat").strip().lower(),
            required_publications=(payload.required_publications or "").strip(),
            required_tools=(payload.required_tools or "").strip(),
            required_parts=(payload.required_parts or "").strip(),
            required_certifications=(payload.required_certifications or "").strip(),
            required_inspection=_flag(payload.required_inspection),
            required_ii=_flag(payload.required_ii),
            required_aca=_flag(payload.required_aca),
            applicability=(payload.applicability or "").strip(),
            status="active",
            revision_label=(payload.revision_label or rev.revision_number).strip(),
            created_at=now,
            updated_at=now,
        )
        self.repo.add_mpd_task(row)
        self._commit_or_conflict(detail="MPD task conflict")
        self.repo.refresh(row)
        return self.mpd_out(row)

    # --- checks ---
    def _compute_check_due(self, check: MaintenanceCheck, util: AircraftUtilization | None) -> None:
        now = _utcnow()
        due_dates: list[datetime] = []
        if check.interval_calendar_days and check.last_done_at:
            due_dates.append(check.last_done_at + timedelta(days=int(check.interval_calendar_days)))
        elif check.interval_calendar_days and not check.last_done_at:
            due_dates.append(now + timedelta(days=int(check.interval_calendar_days)))
        check.next_due_at = min(due_dates) if due_dates else check.next_due_at
        if util and check.interval_flight_hours is not None:
            base = Decimal(str(check.last_done_hours or util.flight_hours or 0))
            check.next_due_hours = base + Decimal(str(check.interval_flight_hours))
        if util and check.interval_flight_cycles is not None:
            base_c = int(check.last_done_cycles or util.flight_cycles or 0)
            check.next_due_cycles = base_c + int(check.interval_flight_cycles)
        # Urgency status
        if check.next_due_at and check.next_due_at < now:
            check.status = "overdue"
        elif check.next_due_at and check.next_due_at <= now + timedelta(days=14):
            if check.status in {"planned", "due"}:
                check.status = "due"

    def list_checks(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[CheckOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        return [
            self.check_out(r)
            for r in self.repo.list_checks(
                organization_id=org_id,
                aircraft_id=filters.get("aircraft_id"),
                status=filters.get("status"),
                limit=int(filters.get("limit") or 100),
                offset=int(filters.get("offset") or 0),
            )
        ]

    def get_check(self, check_id: str, *, username: str, session_role: str) -> CheckOut:
        row = self._require_live(
            self.repo.get_check(check_id), username=username, session_role=session_role, not_found="Maintenance check not found"
        )
        return self.check_out(row)

    def create_check(
        self, payload: CheckCreate, *, username: str, session_role: str, session_org_id: str
    ) -> CheckOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        if payload.check_type not in CHECK_TYPES:
            raise HTTPException(status_code=400, detail="Invalid check type")
        aircraft = self.fleet.get_aircraft(payload.aircraft_id)
        if aircraft is None or aircraft.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Aircraft not found in organization")
        now = _utcnow()
        row = MaintenanceCheck(
            organization_id=org_id,
            program_revision_id=payload.program_revision_id,
            aircraft_id=payload.aircraft_id,
            check_code=payload.check_code.strip().upper(),
            check_type=payload.check_type,
            title=(payload.title or payload.check_code).strip(),
            description=(payload.description or "").strip(),
            interval_calendar_days=payload.interval_calendar_days,
            interval_flight_hours=payload.interval_flight_hours,
            interval_flight_cycles=payload.interval_flight_cycles,
            estimated_duration_hours=payload.estimated_duration_hours or Decimal("0.00"),
            last_done_at=payload.last_done_at,
            last_done_hours=payload.last_done_hours,
            last_done_cycles=payload.last_done_cycles,
            hangar=(payload.hangar or "").strip(),
            bay=(payload.bay or "").strip(),
            shift_code=(payload.shift_code or "").strip(),
            team_name=(payload.team_name or "").strip(),
            supervisor_employee_id=payload.supervisor_employee_id,
            status="planned",
            created_at=now,
            updated_at=now,
        )
        util = self.repo.get_utilization(payload.aircraft_id)
        self._compute_check_due(row, util)
        self.repo.add_check(row)
        self._commit_or_conflict(detail="Check conflict")
        self.repo.refresh(row)
        return self.check_out(row)

    # --- AD / SB / EO ---
    @staticmethod
    def ad_out(row: AirworthinessDirective) -> AdOut:
        return AdOut(
            id=row.id,
            organization_id=row.organization_id,
            ad_number=row.ad_number,
            authority=row.authority,
            manufacturer=row.manufacturer or "",
            revision=row.revision,
            title=row.title,
            applicability=row.applicability or "",
            mandatory=_truthy(row.mandatory),
            compliance_status=row.compliance_status,
            due_date=row.due_date,
            completed_at=row.completed_at,
            publication_id=row.publication_id,
            linked_work_order_id=row.linked_work_order_id,
            history_notes=row.history_notes or "",
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_ads(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[AdOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        return [
            self.ad_out(r)
            for r in self.repo.list_ads(
                organization_id=org_id, limit=int(filters.get("limit") or 100), offset=int(filters.get("offset") or 0)
            )
        ]

    def get_ad(self, ad_id: str, *, username: str, session_role: str) -> AdOut:
        row = self._require_live(
            self.repo.get_ad(ad_id), username=username, session_role=session_role, not_found="Airworthiness directive not found"
        )
        return self.ad_out(row)

    def create_ad(self, payload: AdCreate, *, username: str, session_role: str, session_org_id: str) -> AdOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        now = _utcnow()
        row = AirworthinessDirective(
            organization_id=org_id,
            ad_number=payload.ad_number.strip().upper(),
            authority=payload.authority,
            manufacturer=(payload.manufacturer or "").strip(),
            revision=(payload.revision or "0").strip(),
            title=payload.title.strip(),
            applicability=(payload.applicability or "").strip(),
            mandatory=_flag(payload.mandatory),
            compliance_status="open",
            due_date=payload.due_date,
            publication_id=payload.publication_id,
            history_notes="",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_ad(row)
        self._commit_or_conflict(detail="AD conflict")
        self.repo.refresh(row)
        return self.ad_out(row)

    @staticmethod
    def sb_out(row: ServiceBulletin) -> SbOut:
        return SbOut(
            id=row.id,
            organization_id=row.organization_id,
            sb_number=row.sb_number,
            sb_type=row.sb_type,
            manufacturer=row.manufacturer or "",
            revision=row.revision,
            title=row.title,
            applicability=row.applicability or "",
            priority=row.priority,
            compliance_status=row.compliance_status,
            due_date=row.due_date,
            completed_at=row.completed_at,
            publication_id=row.publication_id,
            linked_work_order_id=row.linked_work_order_id,
            history_notes=row.history_notes or "",
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_sbs(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[SbOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        return [
            self.sb_out(r)
            for r in self.repo.list_sbs(
                organization_id=org_id, limit=int(filters.get("limit") or 100), offset=int(filters.get("offset") or 0)
            )
        ]

    def get_sb(self, sb_id: str, *, username: str, session_role: str) -> SbOut:
        row = self._require_live(
            self.repo.get_sb(sb_id), username=username, session_role=session_role, not_found="Service bulletin not found"
        )
        return self.sb_out(row)

    def create_sb(self, payload: SbCreate, *, username: str, session_role: str, session_org_id: str) -> SbOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        now = _utcnow()
        row = ServiceBulletin(
            organization_id=org_id,
            sb_number=payload.sb_number.strip().upper(),
            sb_type=payload.sb_type,
            manufacturer=(payload.manufacturer or "").strip(),
            revision=(payload.revision or "0").strip(),
            title=payload.title.strip(),
            applicability=(payload.applicability or "").strip(),
            priority=payload.priority,
            compliance_status="open",
            due_date=payload.due_date,
            publication_id=payload.publication_id,
            created_at=now,
            updated_at=now,
        )
        self.repo.add_sb(row)
        self._commit_or_conflict(detail="SB conflict")
        self.repo.refresh(row)
        return self.sb_out(row)

    @staticmethod
    def eo_out(row: EngineeringOrder) -> EoOut:
        return EoOut(
            id=row.id,
            organization_id=row.organization_id,
            eo_number=row.eo_number,
            revision=row.revision,
            title=row.title,
            status=row.status,
            effectivity=row.effectivity or "",
            work_instructions=row.work_instructions or "",
            references=row.references or "",
            publication_id=row.publication_id,
            approved_by=row.approved_by or "",
            approved_at=row.approved_at,
            linked_work_order_id=row.linked_work_order_id,
            due_date=row.due_date,
            history_notes=row.history_notes or "",
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_eos(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[EoOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        return [
            self.eo_out(r)
            for r in self.repo.list_eos(
                organization_id=org_id, limit=int(filters.get("limit") or 100), offset=int(filters.get("offset") or 0)
            )
        ]

    def get_eo(self, eo_id: str, *, username: str, session_role: str) -> EoOut:
        row = self._require_live(
            self.repo.get_eo(eo_id), username=username, session_role=session_role, not_found="Engineering order not found"
        )
        return self.eo_out(row)

    def create_eo(self, payload: EoCreate, *, username: str, session_role: str, session_org_id: str) -> EoOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        now = _utcnow()
        row = EngineeringOrder(
            organization_id=org_id,
            eo_number=payload.eo_number.strip().upper(),
            revision=(payload.revision or "0").strip(),
            title=payload.title.strip(),
            status="draft",
            effectivity=(payload.effectivity or "").strip(),
            work_instructions=(payload.work_instructions or "").strip(),
            references=(payload.references or "").strip(),
            publication_id=payload.publication_id,
            due_date=payload.due_date,
            created_at=now,
            updated_at=now,
        )
        self.repo.add_eo(row)
        self._commit_or_conflict(detail="EO conflict")
        self.repo.refresh(row)
        return self.eo_out(row)

    def approve_eo(self, eo_id: str, *, username: str, session_role: str) -> EoOut:
        row = self.repo.get_eo(eo_id)
        if row is None or row.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Engineering order not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=row.organization_id)
        if row.status not in {"draft", "in_review"}:
            raise HTTPException(status_code=409, detail=f"Cannot approve from status '{row.status}'")
        row.status = "approved"
        row.approved_by = username
        row.approved_at = _utcnow()
        row.updated_at = row.approved_at
        row.history_notes = ((row.history_notes or "") + f"\napproved_by={username}").strip()
        self._commit_or_conflict(detail="EO approve conflict")
        self.repo.refresh(row)
        return self.eo_out(row)

    # --- defects / MEL ---
    @staticmethod
    def defect_out(row: DeferredDefect) -> DefectOut:
        return DefectOut(
            id=row.id,
            organization_id=row.organization_id,
            aircraft_id=row.aircraft_id,
            defect_number=row.defect_number,
            title=row.title,
            description=row.description or "",
            status=row.status,
            deferral_type=row.deferral_type,
            mel_item_id=row.mel_item_id,
            dispatch_category=row.dispatch_category or "",
            repair_interval_hours=row.repair_interval_hours,
            repair_interval_days=row.repair_interval_days,
            expires_at=row.expires_at,
            ata_chapter_id=row.ata_chapter_id,
            linked_work_order_id=row.linked_work_order_id,
            alert_level=row.alert_level,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_defects(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[DefectOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        return [
            self.defect_out(r)
            for r in self.repo.list_defects(
                organization_id=org_id,
                aircraft_id=filters.get("aircraft_id"),
                status=filters.get("status"),
                limit=int(filters.get("limit") or 100),
            )
        ]

    def get_defect(self, defect_id: str, *, username: str, session_role: str) -> DefectOut:
        row = self._require_live(
            self.repo.get_defect(defect_id), username=username, session_role=session_role, not_found="Deferred defect not found"
        )
        return self.defect_out(row)

    def create_defect(
        self, payload: DefectCreate, *, username: str, session_role: str, session_org_id: str
    ) -> DefectOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        aircraft = self.fleet.get_aircraft(payload.aircraft_id)
        if aircraft is None or aircraft.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Aircraft not found")
        if payload.mel_item_id:
            mel = self.repo.get_mel(payload.mel_item_id)
            if mel is None or mel.organization_id != org_id:
                raise HTTPException(status_code=404, detail="MEL/CDL item not found")
        now = _utcnow()
        number = (payload.defect_number or f"DD-{uuid.uuid4().hex[:6].upper()}").strip().upper()
        expires = payload.expires_at
        if expires is None and payload.repair_interval_days:
            expires = now + timedelta(days=int(payload.repair_interval_days))
        row = DeferredDefect(
            organization_id=org_id,
            aircraft_id=payload.aircraft_id,
            defect_number=number,
            title=payload.title.strip(),
            description=(payload.description or "").strip(),
            status="deferred" if payload.deferral_type in {"mel", "cdl"} else "open",
            deferral_type=payload.deferral_type,
            mel_item_id=payload.mel_item_id,
            dispatch_category=(payload.dispatch_category or "").strip().upper(),
            repair_interval_hours=payload.repair_interval_hours,
            repair_interval_days=payload.repair_interval_days,
            expires_at=expires,
            ata_chapter_id=payload.ata_chapter_id,
            alert_level="yellow",
            created_at=now,
            updated_at=now,
        )
        if expires and expires < now + timedelta(days=2):
            row.alert_level = "red"
        self.repo.add_defect(row)
        self._commit_or_conflict(detail="Deferred defect conflict")
        self.repo.refresh(row)
        return self.defect_out(row)

    @staticmethod
    def mel_out(row: MelItem) -> MelItemOut:
        return MelItemOut(
            id=row.id,
            organization_id=row.organization_id,
            list_type=row.list_type,
            item_number=row.item_number,
            title=row.title,
            ata_chapter_id=row.ata_chapter_id,
            dispatch_category=row.dispatch_category,
            repair_interval_days=row.repair_interval_days,
            repair_interval_hours=row.repair_interval_hours,
            dispatch_restrictions=row.dispatch_restrictions or "",
            aircraft_model_id=row.aircraft_model_id,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_mel(self, *, username: str, session_role: str, session_org_id: str, **filters) -> list[MelItemOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=filters.get("organization_id"),
        )
        return [
            self.mel_out(r)
            for r in self.repo.list_mel(
                organization_id=org_id, list_type=filters.get("list_type"), limit=int(filters.get("limit") or 100)
            )
        ]

    def get_mel(self, mel_id: str, *, username: str, session_role: str) -> MelItemOut:
        row = self._require_live(
            self.repo.get_mel(mel_id), username=username, session_role=session_role, not_found="MEL/CDL item not found"
        )
        return self.mel_out(row)

    def create_mel(self, payload: MelItemCreate, *, username: str, session_role: str, session_org_id: str) -> MelItemOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        now = _utcnow()
        row = MelItem(
            organization_id=org_id,
            list_type=payload.list_type,
            item_number=payload.item_number.strip(),
            title=payload.title.strip(),
            ata_chapter_id=payload.ata_chapter_id,
            dispatch_category=payload.dispatch_category,
            repair_interval_days=payload.repair_interval_days,
            repair_interval_hours=payload.repair_interval_hours,
            dispatch_restrictions=(payload.dispatch_restrictions or "").strip(),
            aircraft_model_id=payload.aircraft_model_id,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_mel(row)
        self._commit_or_conflict(detail="MEL item conflict")
        self.repo.refresh(row)
        return self.mel_out(row)

    # --- utilization / hangar ---
    @staticmethod
    def util_out(row: AircraftUtilization) -> UtilizationOut:
        return UtilizationOut(
            id=row.id,
            organization_id=row.organization_id,
            aircraft_id=row.aircraft_id,
            location=row.location or "",
            ops_status=row.ops_status,
            flight_hours=Decimal(str(row.flight_hours or 0)),
            flight_cycles=int(row.flight_cycles or 0),
            landings=int(row.landings or 0),
            engine_hours=Decimal(str(row.engine_hours or 0)),
            apu_hours=Decimal(str(row.apu_hours or 0)),
            traffic_light=row.traffic_light,
            updated_at=row.updated_at,
        )

    def upsert_utilization(
        self, payload: UtilizationUpsert, *, username: str, session_role: str, session_org_id: str
    ) -> UtilizationOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        aircraft = self.fleet.get_aircraft(payload.aircraft_id)
        if aircraft is None or aircraft.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Aircraft not found")
        now = _utcnow()
        row = self.repo.get_utilization(payload.aircraft_id)
        if row is None:
            row = AircraftUtilization(
                organization_id=org_id,
                aircraft_id=payload.aircraft_id,
                created_at=now,
            )
            self.repo.add_utilization(row)
        row.location = (payload.location or "").strip()
        row.ops_status = payload.ops_status
        if payload.flight_hours is not None:
            row.flight_hours = payload.flight_hours
        if payload.flight_cycles is not None:
            row.flight_cycles = payload.flight_cycles
        if payload.landings is not None:
            row.landings = payload.landings
        if payload.engine_hours is not None:
            row.engine_hours = payload.engine_hours
        if payload.apu_hours is not None:
            row.apu_hours = payload.apu_hours
        row.traffic_light = "red" if payload.ops_status == "grounded" else row.traffic_light or "green"
        row.updated_at = now
        self._commit_or_conflict(detail="Utilization conflict")
        self.repo.refresh(row)
        return self.util_out(row)

    def create_hangar_plan(
        self, payload: HangarPlanCreate, *, username: str, session_role: str, session_org_id: str
    ) -> HangarPlanOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        now = _utcnow()
        row = HangarPlan(
            organization_id=org_id,
            aircraft_id=payload.aircraft_id,
            work_package_id=payload.work_package_id,
            hangar=(payload.hangar or "").strip(),
            bay=(payload.bay or "").strip(),
            team_name=(payload.team_name or "").strip(),
            supervisor_employee_id=payload.supervisor_employee_id,
            shift_code=(payload.shift_code or "").strip(),
            estimated_duration_hours=payload.estimated_duration_hours or Decimal("0.00"),
            critical_path=_flag(payload.critical_path),
            capacity_note=(payload.capacity_note or "").strip(),
            scheduled_start=payload.scheduled_start,
            scheduled_finish=payload.scheduled_finish,
            status="planned",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_hangar_plan(row)
        self._commit_or_conflict(detail="Hangar plan conflict")
        self.repo.refresh(row)
        return HangarPlanOut(
            id=row.id,
            organization_id=row.organization_id,
            aircraft_id=row.aircraft_id,
            work_package_id=row.work_package_id,
            hangar=row.hangar,
            bay=row.bay,
            team_name=row.team_name,
            supervisor_employee_id=row.supervisor_employee_id,
            shift_code=row.shift_code,
            estimated_duration_hours=Decimal(str(row.estimated_duration_hours or 0)),
            critical_path=_truthy(row.critical_path),
            capacity_note=row.capacity_note or "",
            scheduled_start=row.scheduled_start,
            scheduled_finish=row.scheduled_finish,
            status=row.status,
            created_at=row.created_at,
        )

    def list_hangar_plans(
        self, *, username: str, session_role: str, session_org_id: str, organization_id: str | None = None
    ) -> list[HangarPlanOut]:
        org_id = self.resolve_org_id(
            username=username, session_role=session_role, session_org_id=session_org_id, requested_org_id=organization_id
        )
        return [
            HangarPlanOut(
                id=r.id,
                organization_id=r.organization_id,
                aircraft_id=r.aircraft_id,
                work_package_id=r.work_package_id,
                hangar=r.hangar,
                bay=r.bay,
                team_name=r.team_name,
                supervisor_employee_id=r.supervisor_employee_id,
                shift_code=r.shift_code,
                estimated_duration_hours=Decimal(str(r.estimated_duration_hours or 0)),
                critical_path=_truthy(r.critical_path),
                capacity_note=r.capacity_note or "",
                scheduled_start=r.scheduled_start,
                scheduled_finish=r.scheduled_finish,
                status=r.status,
                created_at=r.created_at,
            )
            for r in self.repo.list_hangar_plans(org_id)
        ]

    def workforce_out(self, row: WorkforcePlanLine) -> WorkforcePlanLineOut:
        return WorkforcePlanLineOut(
            id=row.id,
            organization_id=row.organization_id,
            work_package_id=row.work_package_id,
            employee_id=row.employee_id,
            role_code=row.role_code,
            shift_code=row.shift_code or "",
            license_ok=_truthy(row.license_ok),
            authorization_ok=_truthy(row.authorization_ok),
            available=_truthy(row.available),
            workload_hours=Decimal(str(row.workload_hours or 0)),
            status=row.status,
            created_at=row.created_at,
        )

    def _require_employee(self, employee_id: str, *, organization_id: str):
        employee = self.work_orders.personnel.get_employee(employee_id)
        if employee is None or employee.organization_id != organization_id:
            raise HTTPException(status_code=404, detail="Employee not found")
        return employee

    def _require_work_package(self, work_package_id: str | None, *, organization_id: str):
        if not work_package_id:
            return None
        package = self.work_orders.repo.get_package(work_package_id)
        if package is None or package.organization_id != organization_id:
            raise HTTPException(status_code=404, detail="Work package not found")
        return package

    def _assign_seed_workforce(
        self, *, organization_id: str, work_package_id: str, shift_code: str = ""
    ) -> None:
        """Planner-entered demo assignments. Flags are not a certification determination."""
        existing = {
            (row.employee_id, row.role_code)
            for row in self.repo.list_workforce_lines(organization_id, work_package_id)
        }
        assignments = (
            ("E-1001", "technician", Decimal("8.00")),
            ("E-2001", "aca", Decimal("2.00")),
            ("E-3001", "ii", Decimal("2.00")),
        )
        now = _utcnow()
        for number, role_code, hours in assignments:
            employee = self.work_orders.personnel.get_by_org_number(organization_id, number)
            if employee is None or (employee.id, role_code) in existing:
                continue
            self.repo.add_workforce_line(
                WorkforcePlanLine(
                    organization_id=organization_id,
                    work_package_id=work_package_id,
                    employee_id=employee.id,
                    role_code=role_code,
                    shift_code=shift_code,
                    license_ok=_flag(True),
                    authorization_ok=_flag(True),
                    available=_flag(True),
                    workload_hours=hours,
                    status="assigned",
                    created_at=now,
                )
            )

    def _ensure_demo_workforce_lines(self, org_id: str) -> None:
        package = self.work_orders.repo.get_package("wp-demo-c-gmea") or self.work_orders.repo.get_package_by_number(
            org_id, "WP-DEMO-001"
        )
        if package is None:
            return
        if self.repo.list_workforce_lines(org_id, package.id):
            return
        self._assign_seed_workforce(
            organization_id=org_id,
            work_package_id=package.id,
            shift_code=package.shift_code or "DAY",
        )
        self.repo.commit()

    def create_workforce_line(
        self, payload: WorkforcePlanLineCreate, *, username: str, session_role: str, session_org_id: str
    ) -> WorkforcePlanLineOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        work_package_id = (payload.work_package_id or "").strip() or None
        self._require_employee(payload.employee_id, organization_id=org_id)
        self._require_work_package(work_package_id, organization_id=org_id)
        row = WorkforcePlanLine(
            organization_id=org_id,
            work_package_id=work_package_id,
            employee_id=payload.employee_id.strip(),
            role_code=payload.role_code,
            shift_code=(payload.shift_code or "").strip(),
            license_ok=_flag(payload.license_ok),
            authorization_ok=_flag(payload.authorization_ok),
            available=_flag(payload.available),
            workload_hours=payload.workload_hours or Decimal("0.00"),
            status=payload.status,
            created_at=_utcnow(),
        )
        self.repo.add_workforce_line(row)
        self._commit_or_conflict(detail="Workforce plan line conflict")
        self.repo.refresh(row)
        return self.workforce_out(row)

    def list_workforce_lines(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
        work_package_id: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[WorkforcePlanLineOut]:
        org_id = self.resolve_org_id(
            username=username, session_role=session_role, session_org_id=session_org_id, requested_org_id=organization_id
        )
        work_package_id = (work_package_id or "").strip() or None
        if work_package_id:
            self._require_work_package(work_package_id, organization_id=org_id)
        return [
            self.workforce_out(row)
            for row in self.repo.list_workforce_lines(
                org_id, work_package_id=work_package_id, limit=limit, offset=offset
            )
        ]

    def get_workforce_line(self, line_id: str, *, username: str, session_role: str) -> WorkforcePlanLineOut:
        row = self._require_live(
            self.repo.get_workforce_line(line_id),
            username=username,
            session_role=session_role,
            not_found="Workforce plan line not found",
        )
        return self.workforce_out(row)

    def update_workforce_line(
        self,
        line_id: str,
        payload: WorkforcePlanLineUpdate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> WorkforcePlanLineOut:
        row = self.repo.get_workforce_line(line_id, for_update=True)
        row = self._require_live(
            row, username=username, session_role=session_role, not_found="Workforce plan line not found"
        )
        org_id = row.organization_id
        self.resolve_org_id(
            username=username, session_role=session_role, session_org_id=session_org_id, requested_org_id=org_id
        )
        updates = payload.model_dump(exclude_unset=True)
        if "work_package_id" in updates:
            raw_wp = updates["work_package_id"]
            work_package_id = (str(raw_wp).strip() or None) if raw_wp else None
            self._require_work_package(work_package_id, organization_id=org_id)
            row.work_package_id = work_package_id
        if "role_code" in updates and updates["role_code"] is not None:
            row.role_code = updates["role_code"]
        if "shift_code" in updates and updates["shift_code"] is not None:
            row.shift_code = str(updates["shift_code"]).strip()
        if "license_ok" in updates and updates["license_ok"] is not None:
            row.license_ok = _flag(bool(updates["license_ok"]))
        if "authorization_ok" in updates and updates["authorization_ok"] is not None:
            row.authorization_ok = _flag(bool(updates["authorization_ok"]))
        if "available" in updates and updates["available"] is not None:
            row.available = _flag(bool(updates["available"]))
        if "workload_hours" in updates and updates["workload_hours"] is not None:
            row.workload_hours = updates["workload_hours"]
        if "status" in updates and updates["status"] is not None:
            row.status = updates["status"]
        self._commit_or_conflict(detail="Workforce plan line conflict")
        self.repo.refresh(row)
        return self.workforce_out(row)

    # --- forecast / due list ---
    def _urgency(self, due_at: datetime | None, *, now: datetime, soon_days: int = 30) -> str:
        if due_at is None:
            return "future"
        if due_at < now:
            return "overdue"
        if due_at <= now + timedelta(days=soon_days):
            return "due_soon"
        return "future"

    def _item(
        self,
        *,
        source_type: str,
        source_id: str,
        aircraft_id: str | None,
        title: str,
        due_basis: str,
        due_at: datetime | None,
        due_hours: Decimal | None = None,
        due_cycles: int | None = None,
        now: datetime,
        util: AircraftUtilization | None = None,
        soon_days: int = 30,
    ) -> ForecastItemOut:
        urgency = self._urgency(due_at, now=now, soon_days=soon_days)
        days_rem = None
        if due_at is not None:
            days_rem = int((due_at - now).total_seconds() // 86400)
        hours_rem = None
        cycles_rem = None
        if util and due_hours is not None:
            hours_rem = Decimal(str(due_hours)) - Decimal(str(util.flight_hours or 0))
            if hours_rem < 0 and urgency == "future":
                urgency = "overdue"
        if util and due_cycles is not None:
            cycles_rem = int(due_cycles) - int(util.flight_cycles or 0)
            if cycles_rem < 0 and urgency == "future":
                urgency = "overdue"
        return ForecastItemOut(
            source_type=source_type,
            source_id=source_id,
            aircraft_id=aircraft_id,
            title=title,
            due_basis=due_basis,
            due_at=due_at,
            due_hours=due_hours,
            due_cycles=due_cycles,
            urgency=urgency,
            days_remaining=days_rem,
            hours_remaining=hours_rem,
            cycles_remaining=cycles_rem,
        )

    def forecast(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
        horizon_days: int = 90,
        aircraft_id: str | None = None,
    ) -> ForecastOut:
        org_id = self.resolve_org_id(
            username=username, session_role=session_role, session_org_id=session_org_id, requested_org_id=organization_id
        )
        now = _utcnow()
        horizon = now + timedelta(days=max(1, min(horizon_days, 3650)))
        util_map = {u.aircraft_id: u for u in self.repo.list_utilization(org_id)}
        items: list[ForecastItemOut] = []

        for chk in self.repo.list_checks(organization_id=org_id, aircraft_id=aircraft_id, limit=500):
            if chk.status in {"completed", "cancelled"}:
                continue
            util = util_map.get(chk.aircraft_id or "")
            items.append(
                self._item(
                    source_type="check",
                    source_id=chk.id,
                    aircraft_id=chk.aircraft_id,
                    title=chk.title or chk.check_code,
                    due_basis="calendar" if chk.next_due_at else "flight_hours",
                    due_at=chk.next_due_at,
                    due_hours=chk.next_due_hours,
                    due_cycles=chk.next_due_cycles,
                    now=now,
                    util=util,
                    soon_days=min(30, horizon_days),
                )
            )

        for ad in self.repo.list_ads(organization_id=org_id, limit=500):
            if ad.compliance_status in {"complied", "cancelled", "superseded"}:
                continue
            if aircraft_id and aircraft_id not in (ad.applicability or ""):
                # still include if applicability empty / family-level
                if ad.applicability and aircraft_id not in ad.applicability:
                    continue
            items.append(
                self._item(
                    source_type="ad",
                    source_id=ad.id,
                    aircraft_id=aircraft_id,
                    title=f"{ad.ad_number}: {ad.title}",
                    due_basis="calendar",
                    due_at=ad.due_date,
                    now=now,
                    soon_days=min(30, horizon_days),
                )
            )

        for sb in self.repo.list_sbs(organization_id=org_id, limit=500):
            if sb.compliance_status in {"complied", "cancelled"}:
                continue
            items.append(
                self._item(
                    source_type="sb",
                    source_id=sb.id,
                    aircraft_id=aircraft_id,
                    title=f"{sb.sb_number}: {sb.title}",
                    due_basis="calendar",
                    due_at=sb.due_date,
                    now=now,
                    soon_days=min(30, horizon_days),
                )
            )

        for eo in self.repo.list_eos(organization_id=org_id, limit=500):
            if eo.status in {"cancelled", "archived"}:
                continue
            items.append(
                self._item(
                    source_type="eo",
                    source_id=eo.id,
                    aircraft_id=aircraft_id,
                    title=f"{eo.eo_number}: {eo.title}",
                    due_basis="calendar",
                    due_at=eo.due_date,
                    now=now,
                    soon_days=min(30, horizon_days),
                )
            )

        for defect in self.repo.list_defects(organization_id=org_id, aircraft_id=aircraft_id, limit=500):
            if defect.status not in {"open", "deferred"}:
                continue
            items.append(
                self._item(
                    source_type="deferred_defect",
                    source_id=defect.id,
                    aircraft_id=defect.aircraft_id,
                    title=f"{defect.defect_number}: {defect.title}",
                    due_basis="calendar",
                    due_at=defect.expires_at,
                    now=now,
                    soon_days=min(30, horizon_days),
                )
            )

        # Filter to horizon for future bucket display; keep overdue always.
        overdue = [i for i in items if i.urgency == "overdue"]
        due_soon = [i for i in items if i.urgency == "due_soon"]
        future = [
            i
            for i in items
            if i.urgency == "future" and (i.due_at is None or i.due_at <= horizon)
        ]
        by_fh = sorted(
            [i for i in items if i.due_hours is not None],
            key=lambda x: (x.hours_remaining is None, x.hours_remaining or Decimal("0")),
        )
        by_fc = sorted(
            [i for i in items if i.due_cycles is not None],
            key=lambda x: (x.cycles_remaining is None, x.cycles_remaining or 0),
        )
        urgency_rank = {"overdue": 0, "due_soon": 1, "future": 2}
        overdue.sort(key=lambda x: x.due_at or now)
        due_soon.sort(key=lambda x: x.due_at or now)
        future.sort(key=lambda x: (urgency_rank.get(x.urgency, 9), x.due_at or horizon))
        return ForecastOut(
            horizon_days=horizon_days,
            generated_at=now,
            overdue=overdue,
            due_soon=due_soon,
            future=future,
            by_flight_hours=by_fh[:100],
            by_flight_cycles=by_fc[:100],
        )

    def due_list(
        self, *, username: str, session_role: str, session_org_id: str, organization_id: str | None = None
    ) -> DueListOut:
        fc = self.forecast(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            organization_id=organization_id,
            horizon_days=180,
        )
        merged = fc.overdue + fc.due_soon + fc.future
        rank = {"overdue": 0, "due_soon": 1, "future": 2}
        merged.sort(key=lambda x: (rank.get(x.urgency, 9), x.due_at or _utcnow()))
        return DueListOut(generated_at=fc.generated_at, items=merged)

    def planner_dashboard(
        self, *, username: str, session_role: str, session_org_id: str, organization_id: str | None = None
    ) -> PlannerDashboardOut:
        org_id = self.resolve_org_id(
            username=username, session_role=session_role, session_org_id=session_org_id, requested_org_id=organization_id
        )
        now = _utcnow()
        soon = now + timedelta(days=30)
        utils = self.repo.list_utilization(org_id)
        grounded = sum(1 for u in utils if u.ops_status == "grounded")
        available = sum(1 for u in utils if u.ops_status == "available")
        lights = {"green": 0, "yellow": 0, "red": 0}
        for u in utils:
            lights[u.traffic_light if u.traffic_light in lights else "green"] += 1

        # Job card wait states from work orders (single aggregated queries via service repo).
        waiting_parts = waiting_eng = waiting_insp = waiting_aca = 0
        try:
            by_status = self.work_orders.repo.count_job_cards_by_status(org_id)
            waiting_parts = int(by_status.get("waiting_parts", 0))
            waiting_eng = int(by_status.get("waiting_engineering", 0))
            waiting_insp = int(by_status.get("waiting_inspection", 0))
            waiting_aca = int(by_status.get("completed", 0))
        except Exception:
            logger.exception("planner dashboard work-order counts failed")

        return PlannerDashboardOut(
            aircraft_count=len(utils),
            grounded=grounded,
            available=available,
            checks_due=self.repo.count_checks_due(org_id, before=soon),
            ads_due=self.repo.count_open_ads_due(org_id, before=soon),
            sbs_due=self.repo.count_open_sbs_due(org_id, before=soon),
            eos_due=self.repo.count_open_eos_due(org_id, before=soon),
            deferred_defects=self.repo.count_deferred(org_id),
            waiting_parts=waiting_parts,
            waiting_engineering=waiting_eng,
            waiting_inspection=waiting_insp,
            waiting_aca=waiting_aca,
            traffic_lights=lights,
        )

    def aircraft_status(
        self, *, username: str, session_role: str, session_org_id: str, organization_id: str | None = None
    ) -> list[AircraftStatusOut]:
        org_id = self.resolve_org_id(
            username=username, session_role=session_role, session_org_id=session_org_id, requested_org_id=organization_id
        )
        out: list[AircraftStatusOut] = []
        for util in self.repo.list_utilization(org_id):
            aircraft = self.fleet.get_aircraft(util.aircraft_id)
            reg = ""
            if aircraft:
                r = self.fleet.get_current_registration(aircraft.id)
                reg = r.registration_mark if r else ""
            open_d = len(self.repo.list_defects(organization_id=org_id, aircraft_id=util.aircraft_id, status="open"))
            def_d = len(self.repo.list_defects(organization_id=org_id, aircraft_id=util.aircraft_id, status="deferred"))
            upcoming = len(
                [
                    c
                    for c in self.repo.list_checks(organization_id=org_id, aircraft_id=util.aircraft_id, limit=50)
                    if c.status in {"planned", "due", "overdue"}
                ]
            )
            maint = "ok"
            if util.ops_status == "grounded" or util.traffic_light == "red":
                maint = "grounded"
            elif upcoming or def_d:
                maint = "attention"
            out.append(
                AircraftStatusOut(
                    aircraft_id=util.aircraft_id,
                    registration=reg,
                    operator=aircraft.operator_id if aircraft else "",
                    fleet_id=aircraft.fleet_id if aircraft else None,
                    location=util.location or "",
                    ops_status=util.ops_status,
                    flight_hours=Decimal(str(util.flight_hours or 0)),
                    flight_cycles=int(util.flight_cycles or 0),
                    engine_hours=Decimal(str(util.engine_hours or 0)),
                    apu_hours=Decimal(str(util.apu_hours or 0)),
                    open_defects=open_d,
                    deferred_defects=def_d,
                    upcoming_checks=upcoming,
                    traffic_light=util.traffic_light,
                    maintenance_status=maint,
                )
            )
        return out

    # --- automatic work package generation ---
    def generate_work_package_from_check(
        self,
        payload: GeneratePackageRequest,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> GeneratePackageOut:
        check = self.repo.get_check(payload.check_id, for_update=True)
        if check is None or check.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Maintenance check not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=check.organization_id)
        if not check.aircraft_id:
            raise HTTPException(status_code=409, detail="Check has no aircraft")
        if check.generated_work_package_id:
            raise HTTPException(status_code=409, detail="Work package already generated for this check")

        pkg = self.work_orders.create_package(
            WorkPackageCreate(
                organization_id=check.organization_id,
                aircraft_id=check.aircraft_id,
                description=f"{check.check_type.upper()} check {check.check_code}: {check.title}",
                priority="high" if check.status in {"due", "overdue"} else "normal",
                hangar_bay=check.bay or "",
                shift_code=check.shift_code or "",
                supervisor_employee_id=check.supervisor_employee_id,
                estimated_hours=check.estimated_duration_hours,
                scheduled_start=check.next_due_at,
            ),
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
        )
        order = self.work_orders.create_order(
            WorkOrderCreate(
                work_package_id=pkg.id,
                title=f"{check.check_code} work order",
                description=check.description or check.title,
                ata_chapter_id=None,
                priority=pkg.priority,
                estimated_hours=check.estimated_duration_hours,
            ),
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
        )
        job_card_ids: list[str] = []
        if payload.include_mpd_tasks and check.program_revision_id:
            tasks = self.repo.list_mpd_tasks(
                organization_id=check.organization_id,
                program_revision_id=check.program_revision_id,
                limit=payload.max_job_cards,
            )
            for task in tasks[: payload.max_job_cards]:
                card = self.work_orders.create_job_card(
                    JobCardCreate(
                        work_order_id=order.id,
                        title=task.title,
                        description=task.description,
                        ata_chapter_id=task.ata_chapter_id,
                        estimated_hours=task.estimated_manhours,
                        required_parts=task.required_parts,
                        required_tools=task.required_tools,
                        required_skills=task.required_skill,
                        required_certification=task.required_certifications,
                        independent_inspection_required=_truthy(task.required_ii),
                        aca_required=_truthy(task.required_aca),
                        hangar_bay=check.bay or "",
                    ),
                    username=username,
                    session_role=session_role,
                    session_org_id=session_org_id,
                )
                job_card_ids.append(card.id)
                if task.required_parts:
                    self.repo.add_parts_line(
                        PartsPlanLine(
                            organization_id=check.organization_id,
                            work_package_id=pkg.id,
                            mpd_task_id=task.id,
                            part_number=task.required_parts[:120],
                            description=task.title,
                            qty_required=1,
                            qty_available=0,
                            status="shortage",
                        )
                    )
                if task.required_tools:
                    self.repo.add_tool_line(
                        ToolPlanLine(
                            organization_id=check.organization_id,
                            work_package_id=pkg.id,
                            tool_code=task.required_tools[:120],
                            description=task.title,
                            calibration_status="current",
                            status="reserved",
                        )
                    )
            # Program B: live reserve / shortage / tool planning against logistics
            self.db.flush()
            self._apply_logistics_planning(
                organization_id=check.organization_id,
                work_package_id=pkg.id,
                username=username,
            )
        else:
            card = self.work_orders.create_job_card(
                JobCardCreate(
                    work_order_id=order.id,
                    title=check.title or check.check_code,
                    description=check.description or "",
                    hangar_bay=check.bay or "",
                    estimated_hours=check.estimated_duration_hours,
                ),
                username=username,
                session_role=session_role,
                session_org_id=session_org_id,
            )
            job_card_ids.append(card.id)

        # Hangar + workforce plan lines for the generated package
        self.repo.add_hangar_plan(
            HangarPlan(
                organization_id=check.organization_id,
                aircraft_id=check.aircraft_id,
                work_package_id=pkg.id,
                hangar=check.hangar or "",
                bay=check.bay or "",
                team_name=check.team_name or "",
                supervisor_employee_id=check.supervisor_employee_id,
                shift_code=check.shift_code or "",
                estimated_duration_hours=check.estimated_duration_hours,
                critical_path=_flag(check.status == "overdue"),
                scheduled_start=check.next_due_at,
                status="planned",
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
        )
        self._assign_seed_workforce(
            organization_id=check.organization_id,
            work_package_id=pkg.id,
            shift_code=check.shift_code or "",
        )
        check.generated_work_package_id = pkg.id
        check.status = "in_work"
        check.updated_at = _utcnow()
        self._commit_or_conflict(detail="Generate package conflict")
        return GeneratePackageOut(
            work_package_id=pkg.id,
            package_number=pkg.package_number,
            work_order_ids=[order.id],
            job_card_ids=job_card_ids,
            check_id=check.id,
        )
