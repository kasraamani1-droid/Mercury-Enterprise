from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..shared import clamp_page
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


class PlanningRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)

    def flush(self) -> None:
        self.db.flush()

    # --- programs ---
    def add_program(self, row: MaintenanceProgram) -> MaintenanceProgram:
        self.db.add(row)
        return row

    def get_program(self, program_id: str, *, for_update: bool = False) -> MaintenanceProgram | None:
        stmt = select(MaintenanceProgram).where(MaintenanceProgram.id == program_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def get_program_by_code(self, org_id: str, code: str) -> MaintenanceProgram | None:
        return self.db.scalars(
            select(MaintenanceProgram).where(
                MaintenanceProgram.organization_id == org_id,
                MaintenanceProgram.program_code == code,
                MaintenanceProgram.deleted_at.is_(None),
            )
        ).first()

    def list_programs(self, *, organization_id: str, limit: int = 100, offset: int = 0) -> list[MaintenanceProgram]:
        return list(
            self.db.scalars(
                select(MaintenanceProgram)
                .where(
                    MaintenanceProgram.organization_id == organization_id,
                    MaintenanceProgram.deleted_at.is_(None),
                )
                .order_by(MaintenanceProgram.program_code)
                .limit(min(max(limit, 1), 500))
                .offset(max(offset, 0))
            ).all()
        )

    def add_revision(self, row: MaintenanceProgramRevision) -> MaintenanceProgramRevision:
        self.db.add(row)
        return row

    def get_revision(self, revision_id: str) -> MaintenanceProgramRevision | None:
        return self.db.get(MaintenanceProgramRevision, revision_id)

    def list_revisions(self, program_id: str) -> list[MaintenanceProgramRevision]:
        return list(
            self.db.scalars(
                select(MaintenanceProgramRevision)
                .where(MaintenanceProgramRevision.program_id == program_id)
                .order_by(MaintenanceProgramRevision.created_at.desc())
            ).all()
        )

    # --- mpd ---
    def add_mpd_task(self, row: MpdTask) -> MpdTask:
        self.db.add(row)
        return row

    def get_mpd_task(self, task_id: str) -> MpdTask | None:
        return self.db.get(MpdTask, task_id)

    def list_mpd_tasks(
        self, *, organization_id: str, program_revision_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[MpdTask]:
        stmt: Select[tuple[MpdTask]] = select(MpdTask).where(
            MpdTask.organization_id == organization_id,
            MpdTask.deleted_at.is_(None),
        )
        if program_revision_id:
            stmt = stmt.where(MpdTask.program_revision_id == program_revision_id)
        return list(
            self.db.scalars(stmt.order_by(MpdTask.task_number).limit(min(max(limit, 1), 500)).offset(max(offset, 0))).all()
        )

    # --- checks ---
    def add_check(self, row: MaintenanceCheck) -> MaintenanceCheck:
        self.db.add(row)
        return row

    def get_check(self, check_id: str, *, for_update: bool = False) -> MaintenanceCheck | None:
        stmt = select(MaintenanceCheck).where(MaintenanceCheck.id == check_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_checks(
        self,
        *,
        organization_id: str,
        aircraft_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MaintenanceCheck]:
        stmt = select(MaintenanceCheck).where(
            MaintenanceCheck.organization_id == organization_id,
            MaintenanceCheck.deleted_at.is_(None),
        )
        if aircraft_id:
            stmt = stmt.where(MaintenanceCheck.aircraft_id == aircraft_id)
        if status:
            stmt = stmt.where(MaintenanceCheck.status == status)
        return list(
            self.db.scalars(
                stmt.order_by(MaintenanceCheck.next_due_at.asc().nullslast())
                .limit(min(max(limit, 1), 500))
                .offset(max(offset, 0))
            ).all()
        )

    def count_checks_due(self, organization_id: str, *, before: datetime) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(MaintenanceCheck)
                .where(
                    MaintenanceCheck.organization_id == organization_id,
                    MaintenanceCheck.deleted_at.is_(None),
                    MaintenanceCheck.status.in_(("planned", "due", "overdue")),
                    MaintenanceCheck.next_due_at.is_not(None),
                    MaintenanceCheck.next_due_at <= before,
                )
            )
            or 0
        )

    # --- AD/SB/EO ---
    def add_ad(self, row: AirworthinessDirective) -> AirworthinessDirective:
        self.db.add(row)
        return row

    def get_ad(self, ad_id: str) -> AirworthinessDirective | None:
        return self.db.get(AirworthinessDirective, ad_id)

    def list_ads(self, *, organization_id: str, limit: int = 100, offset: int = 0) -> list[AirworthinessDirective]:
        return list(
            self.db.scalars(
                select(AirworthinessDirective)
                .where(
                    AirworthinessDirective.organization_id == organization_id,
                    AirworthinessDirective.deleted_at.is_(None),
                )
                .order_by(AirworthinessDirective.due_date.asc().nullslast())
                .limit(min(max(limit, 1), 500))
                .offset(max(offset, 0))
            ).all()
        )

    def add_sb(self, row: ServiceBulletin) -> ServiceBulletin:
        self.db.add(row)
        return row

    def get_sb(self, sb_id: str) -> ServiceBulletin | None:
        return self.db.get(ServiceBulletin, sb_id)

    def list_sbs(self, *, organization_id: str, limit: int = 100, offset: int = 0) -> list[ServiceBulletin]:
        return list(
            self.db.scalars(
                select(ServiceBulletin)
                .where(ServiceBulletin.organization_id == organization_id, ServiceBulletin.deleted_at.is_(None))
                .order_by(ServiceBulletin.due_date.asc().nullslast())
                .limit(min(max(limit, 1), 500))
                .offset(max(offset, 0))
            ).all()
        )

    def add_eo(self, row: EngineeringOrder) -> EngineeringOrder:
        self.db.add(row)
        return row

    def get_eo(self, eo_id: str) -> EngineeringOrder | None:
        return self.db.get(EngineeringOrder, eo_id)

    def list_eos(self, *, organization_id: str, limit: int = 100, offset: int = 0) -> list[EngineeringOrder]:
        return list(
            self.db.scalars(
                select(EngineeringOrder)
                .where(EngineeringOrder.organization_id == organization_id, EngineeringOrder.deleted_at.is_(None))
                .order_by(EngineeringOrder.due_date.asc().nullslast())
                .limit(min(max(limit, 1), 500))
                .offset(max(offset, 0))
            ).all()
        )

    def count_open_ads_due(self, organization_id: str, *, before: datetime) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(AirworthinessDirective)
                .where(
                    AirworthinessDirective.organization_id == organization_id,
                    AirworthinessDirective.deleted_at.is_(None),
                    AirworthinessDirective.compliance_status.in_(("open", "planned")),
                    AirworthinessDirective.due_date.is_not(None),
                    AirworthinessDirective.due_date <= before,
                )
            )
            or 0
        )

    def count_open_sbs_due(self, organization_id: str, *, before: datetime) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(ServiceBulletin)
                .where(
                    ServiceBulletin.organization_id == organization_id,
                    ServiceBulletin.deleted_at.is_(None),
                    ServiceBulletin.compliance_status.in_(("open", "planned")),
                    ServiceBulletin.due_date.is_not(None),
                    ServiceBulletin.due_date <= before,
                )
            )
            or 0
        )

    def count_open_eos_due(self, organization_id: str, *, before: datetime) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(EngineeringOrder)
                .where(
                    EngineeringOrder.organization_id == organization_id,
                    EngineeringOrder.deleted_at.is_(None),
                    EngineeringOrder.status.in_(("draft", "in_review", "approved", "released")),
                    EngineeringOrder.due_date.is_not(None),
                    EngineeringOrder.due_date <= before,
                )
            )
            or 0
        )

    # --- defects / mel ---
    def add_defect(self, row: DeferredDefect) -> DeferredDefect:
        self.db.add(row)
        return row

    def get_defect(self, defect_id: str) -> DeferredDefect | None:
        return self.db.get(DeferredDefect, defect_id)

    def list_defects(
        self,
        *,
        organization_id: str,
        aircraft_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[DeferredDefect]:
        lim, _ = clamp_page(limit, 0)
        stmt = select(DeferredDefect).where(
            DeferredDefect.organization_id == organization_id,
            DeferredDefect.deleted_at.is_(None),
        )
        if aircraft_id:
            stmt = stmt.where(DeferredDefect.aircraft_id == aircraft_id)
        if status:
            stmt = stmt.where(DeferredDefect.status == status)
        return list(self.db.scalars(stmt.order_by(DeferredDefect.expires_at.asc().nullslast()).limit(lim)).all())

    def count_deferred(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(DeferredDefect)
                .where(
                    DeferredDefect.organization_id == organization_id,
                    DeferredDefect.deleted_at.is_(None),
                    DeferredDefect.status.in_(("open", "deferred")),
                )
            )
            or 0
        )

    def add_mel(self, row: MelItem) -> MelItem:
        self.db.add(row)
        return row

    def get_mel(self, mel_id: str) -> MelItem | None:
        return self.db.get(MelItem, mel_id)

    def list_mel(self, *, organization_id: str, list_type: str | None = None, limit: int = 100) -> list[MelItem]:
        lim, _ = clamp_page(limit, 0)
        stmt = select(MelItem).where(MelItem.organization_id == organization_id, MelItem.deleted_at.is_(None))
        if list_type:
            stmt = stmt.where(MelItem.list_type == list_type)
        return list(self.db.scalars(stmt.order_by(MelItem.item_number).limit(lim)).all())

    # --- utilization / hangar / plans ---
    def get_utilization(self, aircraft_id: str) -> AircraftUtilization | None:
        return self.db.scalars(
            select(AircraftUtilization).where(AircraftUtilization.aircraft_id == aircraft_id)
        ).first()

    def list_utilization(self, organization_id: str) -> list[AircraftUtilization]:
        return list(
            self.db.scalars(
                select(AircraftUtilization).where(AircraftUtilization.organization_id == organization_id)
            ).all()
        )

    def add_utilization(self, row: AircraftUtilization) -> AircraftUtilization:
        self.db.add(row)
        return row

    def add_hangar_plan(self, row: HangarPlan) -> HangarPlan:
        self.db.add(row)
        return row

    def list_hangar_plans(self, organization_id: str, limit: int = 100) -> list[HangarPlan]:
        lim, _ = clamp_page(limit, 0)
        return list(
            self.db.scalars(
                select(HangarPlan)
                .where(HangarPlan.organization_id == organization_id)
                .order_by(HangarPlan.scheduled_start.asc().nullslast())
                .limit(lim)
            ).all()
        )

    def add_parts_line(self, row: PartsPlanLine) -> PartsPlanLine:
        self.db.add(row)
        return row

    def list_parts_lines(self, organization_id: str, work_package_id: str | None = None) -> list[PartsPlanLine]:
        stmt = select(PartsPlanLine).where(PartsPlanLine.organization_id == organization_id)
        if work_package_id:
            stmt = stmt.where(PartsPlanLine.work_package_id == work_package_id)
        return list(self.db.scalars(stmt).all())

    def add_tool_line(self, row: ToolPlanLine) -> ToolPlanLine:
        self.db.add(row)
        return row

    def list_tool_lines(self, organization_id: str, work_package_id: str | None = None) -> list[ToolPlanLine]:
        stmt = select(ToolPlanLine).where(ToolPlanLine.organization_id == organization_id)
        if work_package_id:
            stmt = stmt.where(ToolPlanLine.work_package_id == work_package_id)
        return list(self.db.scalars(stmt).all())

    def add_workforce_line(self, row: WorkforcePlanLine) -> WorkforcePlanLine:
        self.db.add(row)
        return row

    def list_workforce_lines(self, organization_id: str, work_package_id: str | None = None) -> list[WorkforcePlanLine]:
        stmt = select(WorkforcePlanLine).where(WorkforcePlanLine.organization_id == organization_id)
        if work_package_id:
            stmt = stmt.where(WorkforcePlanLine.work_package_id == work_package_id)
        return list(self.db.scalars(stmt).all())
