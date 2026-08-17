"""Sprint 9 planning domain models — revision-controlled, soft-deletable where noted."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..models import uid


class MaintenanceProgram(Base):
    """Operator/manufacturer maintenance program header (revision-controlled)."""

    __tablename__ = "maintenance_programs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    program_code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    manufacturer: Mapped[str] = mapped_column(String(120), default="")
    aircraft_family: Mapped[str] = mapped_column(String(120), default="")
    aircraft_model_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    operator_name: Mapped[str] = mapped_column(String(200), default="")
    # draft | active | superseded | archived
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    current_revision_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    revisions: Mapped[list["MaintenanceProgramRevision"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", order_by="MaintenanceProgramRevision.created_at"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "program_code", name="uq_maint_program_org_code"),
        Index("ix_maint_programs_org_status", "organization_id", "status"),
    )


class MaintenanceProgramRevision(Base):
    """Immutable program revision — never overwrite."""

    __tablename__ = "maintenance_program_revisions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    program_id: Mapped[str] = mapped_column(ForeignKey("maintenance_programs.id"), index=True)
    revision_number: Mapped[str] = mapped_column(String(40))
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approval_authority: Mapped[str] = mapped_column(String(120), default="")
    approval_reference: Mapped[str] = mapped_column(String(200), default="")
    # draft | approved | active | superseded | archived
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    program: Mapped[MaintenanceProgram] = relationship(back_populates="revisions")

    __table_args__ = (
        UniqueConstraint("program_id", "revision_number", name="uq_maint_program_rev"),
        Index("ix_maint_program_revs_org", "organization_id", "status"),
    )


class MpdTask(Base):
    """Maintenance Planning Document task line."""

    __tablename__ = "mpd_tasks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    program_revision_id: Mapped[str] = mapped_column(
        ForeignKey("maintenance_program_revisions.id"), index=True
    )
    task_number: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300))
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    required_skill: Mapped[str] = mapped_column(String(200), default="")
    estimated_manhours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    # Interval / threshold units
    interval_calendar_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_flight_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    interval_flight_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_landings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_engine_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    interval_apu_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    interval_component_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    threshold_flight_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    threshold_flight_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    threshold_calendar_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # once | repeat
    repeat_policy: Mapped[str] = mapped_column(String(40), default="repeat")
    required_publications: Mapped[str] = mapped_column(Text, default="")
    required_tools: Mapped[str] = mapped_column(Text, default="")
    required_parts: Mapped[str] = mapped_column(Text, default="")
    required_certifications: Mapped[str] = mapped_column(String(200), default="")
    required_inspection: Mapped[str] = mapped_column(String(10), default="true")
    required_ii: Mapped[str] = mapped_column(String(10), default="false")
    required_aca: Mapped[str] = mapped_column(String(10), default="true")
    applicability: Mapped[str] = mapped_column(Text, default="")
    # active | superseded | archived
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    revision_label: Mapped[str] = mapped_column(String(40), default="")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("program_revision_id", "task_number", name="uq_mpd_task_rev_number"),
        Index("ix_mpd_tasks_org_status", "organization_id", "status"),
        Index("ix_mpd_tasks_org_ata", "organization_id", "ata_chapter_id"),
    )


class MaintenanceCheck(Base):
    """Scheduled check definition / instance planning."""

    __tablename__ = "maintenance_checks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    program_revision_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    aircraft_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    check_code: Mapped[str] = mapped_column(String(80), index=True)
    # preflight|transit|daily|weekly|service|a|b|c|d|structural|engine|landing_gear|special|custom
    check_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    interval_calendar_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_flight_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    interval_flight_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_duration_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    last_done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_done_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    last_done_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    next_due_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    next_due_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # planned | due | overdue | in_work | completed | cancelled
    status: Mapped[str] = mapped_column(String(40), default="planned", index=True)
    generated_work_package_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    hangar: Mapped[str] = mapped_column(String(80), default="")
    bay: Mapped[str] = mapped_column(String(80), default="")
    shift_code: Mapped[str] = mapped_column(String(40), default="")
    team_name: Mapped[str] = mapped_column(String(120), default="")
    supervisor_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_maint_checks_org_aircraft", "organization_id", "aircraft_id"),
        Index("ix_maint_checks_org_due", "organization_id", "next_due_at"),
        Index("ix_maint_checks_org_type", "organization_id", "check_type"),
    )


class AirworthinessDirective(Base):
    __tablename__ = "airworthiness_directives"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    ad_number: Mapped[str] = mapped_column(String(80), index=True)
    # faa | easa | transport_canada | manufacturer | other
    authority: Mapped[str] = mapped_column(String(40), index=True)
    manufacturer: Mapped[str] = mapped_column(String(120), default="")
    revision: Mapped[str] = mapped_column(String(40), default="0")
    title: Mapped[str] = mapped_column(String(300), default="")
    applicability: Mapped[str] = mapped_column(Text, default="")
    mandatory: Mapped[str] = mapped_column(String(10), default="true")
    # open | planned | complied | superseded | cancelled
    compliance_status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    publication_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    linked_work_order_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    history_notes: Mapped[str] = mapped_column(Text, default="")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "ad_number", "revision", name="uq_ad_org_number_rev"),
        Index("ix_ad_org_status", "organization_id", "compliance_status"),
    )


class ServiceBulletin(Base):
    __tablename__ = "service_bulletins"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    sb_number: Mapped[str] = mapped_column(String(80), index=True)
    # sb | asb | csb | rsb
    sb_type: Mapped[str] = mapped_column(String(20), default="sb", index=True)
    manufacturer: Mapped[str] = mapped_column(String(120), default="")
    revision: Mapped[str] = mapped_column(String(40), default="0")
    title: Mapped[str] = mapped_column(String(300), default="")
    applicability: Mapped[str] = mapped_column(Text, default="")
    # recommended | mandatory
    priority: Mapped[str] = mapped_column(String(40), default="recommended")
    compliance_status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    publication_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    linked_work_order_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    history_notes: Mapped[str] = mapped_column(Text, default="")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "sb_number", "revision", name="uq_sb_org_number_rev"),
        Index("ix_sb_org_status", "organization_id", "compliance_status"),
    )


class EngineeringOrder(Base):
    __tablename__ = "engineering_orders"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    eo_number: Mapped[str] = mapped_column(String(80), index=True)
    revision: Mapped[str] = mapped_column(String(40), default="0")
    title: Mapped[str] = mapped_column(String(300), default="")
    # draft | in_review | approved | released | cancelled | archived
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    effectivity: Mapped[str] = mapped_column(Text, default="")
    work_instructions: Mapped[str] = mapped_column(Text, default="")
    references: Mapped[str] = mapped_column(Text, default="")
    publication_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    linked_work_order_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    history_notes: Mapped[str] = mapped_column(Text, default="")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "eo_number", "revision", name="uq_eo_org_number_rev"),
        Index("ix_eo_org_status", "organization_id", "status"),
    )


class DeferredDefect(Base):
    __tablename__ = "deferred_defects"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    aircraft_id: Mapped[str] = mapped_column(String(80), index=True)
    defect_number: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    # open | deferred | transferred | completed | cancelled | closed
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    # mel | cdl | other
    deferral_type: Mapped[str] = mapped_column(String(40), default="mel")
    mel_item_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    # A | B | C | D
    dispatch_category: Mapped[str] = mapped_column(String(10), default="")
    repair_interval_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    repair_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    linked_work_order_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    alert_level: Mapped[str] = mapped_column(String(20), default="yellow")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "defect_number", name="uq_deferred_defect_org_number"),
        Index("ix_deferred_defects_org_aircraft", "organization_id", "aircraft_id"),
        Index("ix_deferred_defects_org_status", "organization_id", "status"),
    )


class MelItem(Base):
    """MMEL / MEL or CDL item."""

    __tablename__ = "mel_items"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    # mel | cdl
    list_type: Mapped[str] = mapped_column(String(20), default="mel", index=True)
    item_number: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # A | B | C | D
    dispatch_category: Mapped[str] = mapped_column(String(10), default="C")
    repair_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repair_interval_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    dispatch_restrictions: Mapped[str] = mapped_column(Text, default="")
    aircraft_model_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "list_type", "item_number", name="uq_mel_org_type_item"),
        Index("ix_mel_items_org_cat", "organization_id", "dispatch_category"),
    )


class AircraftUtilization(Base):
    """Airframe utilization counters for forecast (additive; does not alter fleet.Aircraft)."""

    __tablename__ = "aircraft_utilization"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    aircraft_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    location: Mapped[str] = mapped_column(String(120), default="")
    # available | grounded | maintenance | ferry
    ops_status: Mapped[str] = mapped_column(String(40), default="available", index=True)
    flight_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    flight_cycles: Mapped[int] = mapped_column(Integer, default=0)
    landings: Mapped[int] = mapped_column(Integer, default=0)
    engine_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    apu_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    # green | yellow | red
    traffic_light: Mapped[str] = mapped_column(String(20), default="green")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_aircraft_util_org_status", "organization_id", "ops_status"),)


class HangarPlan(Base):
    __tablename__ = "hangar_plans"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    aircraft_id: Mapped[str] = mapped_column(String(80), index=True)
    work_package_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    hangar: Mapped[str] = mapped_column(String(80), default="")
    bay: Mapped[str] = mapped_column(String(80), default="")
    team_name: Mapped[str] = mapped_column(String(120), default="")
    supervisor_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    shift_code: Mapped[str] = mapped_column(String(40), default="")
    estimated_duration_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    critical_path: Mapped[str] = mapped_column(String(10), default="false")
    capacity_note: Mapped[str] = mapped_column(String(300), default="")
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_finish: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="planned", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_hangar_plans_org_aircraft", "organization_id", "aircraft_id"),)


class PartsPlanLine(Base):
    __tablename__ = "parts_plan_lines"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    work_package_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    mpd_task_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    part_number: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(String(300), default="")
    qty_required: Mapped[int] = mapped_column(Integer, default=1)
    qty_available: Mapped[int] = mapped_column(Integer, default=0)
    qty_reserved: Mapped[int] = mapped_column(Integer, default=0)
    # ok | shortage | purchase_required | ordered | issued | returned
    status: Mapped[str] = mapped_column(String(40), default="ok", index=True)
    expected_delivery: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ToolPlanLine(Base):
    __tablename__ = "tool_plan_lines"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    work_package_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    tool_code: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(String(300), default="")
    calibration_status: Mapped[str] = mapped_column(String(40), default="current")
    calibration_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # available | reserved | issued | returned | overdue_cal
    status: Mapped[str] = mapped_column(String(40), default="available", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkforcePlanLine(Base):
    __tablename__ = "workforce_plan_lines"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    work_package_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    employee_id: Mapped[str] = mapped_column(String(80), index=True)
    # technician | inspector | ii | aca | engineer | stores
    role_code: Mapped[str] = mapped_column(String(40), index=True)
    shift_code: Mapped[str] = mapped_column(String(40), default="")
    license_ok: Mapped[str] = mapped_column(String(10), default="true")
    authorization_ok: Mapped[str] = mapped_column(String(10), default="true")
    available: Mapped[str] = mapped_column(String(10), default="true")
    workload_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(40), default="assigned", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_workforce_plan_org_wp", "organization_id", "work_package_id"),)
