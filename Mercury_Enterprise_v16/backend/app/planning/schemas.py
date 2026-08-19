from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProgramCreate(BaseModel):
    organization_id: str | None = None
    program_code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    manufacturer: str = ""
    aircraft_family: str = ""
    aircraft_model_id: str | None = None
    operator_name: str = ""
    revision_number: str = "1"
    effective_date: datetime | None = None
    approval_authority: str = ""
    approval_reference: str = ""


class ProgramRevisionCreate(BaseModel):
    revision_number: str = Field(min_length=1, max_length=40)
    effective_date: datetime | None = None
    approval_authority: str = ""
    approval_reference: str = ""
    notes: str = ""
    activate: bool = False


class ProgramOut(BaseModel):
    id: str
    organization_id: str
    program_code: str
    title: str
    manufacturer: str
    aircraft_family: str
    aircraft_model_id: str | None
    operator_name: str
    status: str
    current_revision_id: str | None
    created_at: datetime
    updated_at: datetime


class ProgramRevisionOut(BaseModel):
    id: str
    organization_id: str
    program_id: str
    revision_number: str
    effective_date: datetime | None
    approval_authority: str
    approval_reference: str
    status: str
    notes: str
    created_at: datetime


class MpdTaskCreate(BaseModel):
    program_revision_id: str
    task_number: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    ata_chapter_id: str | None = None
    description: str = ""
    required_skill: str = ""
    estimated_manhours: Decimal = Field(default=Decimal("0.00"), ge=0)
    interval_calendar_days: int | None = Field(default=None, ge=1)
    interval_flight_hours: Decimal | None = Field(default=None, ge=0)
    interval_flight_cycles: int | None = Field(default=None, ge=0)
    interval_landings: int | None = None
    interval_engine_hours: Decimal | None = None
    interval_apu_hours: Decimal | None = None
    interval_component_hours: Decimal | None = None
    threshold_flight_hours: Decimal | None = None
    threshold_flight_cycles: int | None = None
    threshold_calendar_days: int | None = None
    repeat_policy: str = "repeat"
    required_publications: str = ""
    required_tools: str = ""
    required_parts: str = ""
    required_certifications: str = ""
    required_inspection: bool = True
    required_ii: bool = False
    required_aca: bool = True
    applicability: str = ""
    revision_label: str = ""


class MpdTaskOut(BaseModel):
    id: str
    organization_id: str
    program_revision_id: str
    task_number: str
    title: str
    ata_chapter_id: str | None
    description: str
    required_skill: str
    estimated_manhours: Decimal
    interval_calendar_days: int | None
    interval_flight_hours: Decimal | None
    interval_flight_cycles: int | None
    interval_landings: int | None
    interval_engine_hours: Decimal | None
    interval_apu_hours: Decimal | None
    interval_component_hours: Decimal | None
    threshold_flight_hours: Decimal | None
    threshold_flight_cycles: int | None
    threshold_calendar_days: int | None
    repeat_policy: str
    required_publications: str
    required_tools: str
    required_parts: str
    required_certifications: str
    required_inspection: bool
    required_ii: bool
    required_aca: bool
    applicability: str
    status: str
    revision_label: str
    created_at: datetime
    updated_at: datetime


class CheckCreate(BaseModel):
    organization_id: str | None = None
    program_revision_id: str | None = None
    aircraft_id: str
    check_code: str = Field(min_length=1, max_length=80)
    check_type: str = Field(
        pattern="^(preflight|transit|daily|weekly|service|a|b|c|d|structural|engine|landing_gear|special|custom)$"
    )
    title: str = ""
    description: str = ""
    interval_calendar_days: int | None = None
    interval_flight_hours: Decimal | None = None
    interval_flight_cycles: int | None = None
    estimated_duration_hours: Decimal = Field(default=Decimal("8.00"), ge=0)
    last_done_at: datetime | None = None
    last_done_hours: Decimal | None = None
    last_done_cycles: int | None = None
    hangar: str = ""
    bay: str = ""
    shift_code: str = ""
    team_name: str = ""
    supervisor_employee_id: str | None = None


class CheckOut(BaseModel):
    id: str
    organization_id: str
    program_revision_id: str | None
    aircraft_id: str | None
    check_code: str
    check_type: str
    title: str
    description: str
    interval_calendar_days: int | None
    interval_flight_hours: Decimal | None
    interval_flight_cycles: int | None
    estimated_duration_hours: Decimal
    last_done_at: datetime | None
    last_done_hours: Decimal | None
    last_done_cycles: int | None
    next_due_at: datetime | None
    next_due_hours: Decimal | None
    next_due_cycles: int | None
    status: str
    generated_work_package_id: str | None
    hangar: str
    bay: str
    shift_code: str
    team_name: str
    supervisor_employee_id: str | None
    created_at: datetime
    updated_at: datetime


class AdCreate(BaseModel):
    organization_id: str | None = None
    ad_number: str = Field(min_length=1, max_length=80)
    authority: str = Field(pattern="^(faa|easa|transport_canada|manufacturer|other)$")
    manufacturer: str = ""
    revision: str = "0"
    title: str = Field(min_length=1, max_length=300)
    applicability: str = ""
    mandatory: bool = True
    due_date: datetime | None = None
    publication_id: str | None = None


class AdOut(BaseModel):
    id: str
    organization_id: str
    ad_number: str
    authority: str
    manufacturer: str
    revision: str
    title: str
    applicability: str
    mandatory: bool
    compliance_status: str
    due_date: datetime | None
    completed_at: datetime | None
    publication_id: str | None
    linked_work_order_id: str | None
    history_notes: str
    created_at: datetime
    updated_at: datetime


class SbCreate(BaseModel):
    organization_id: str | None = None
    sb_number: str = Field(min_length=1, max_length=80)
    sb_type: str = Field(default="sb", pattern="^(sb|asb|csb|rsb)$")
    manufacturer: str = ""
    revision: str = "0"
    title: str = Field(min_length=1, max_length=300)
    applicability: str = ""
    priority: str = Field(default="recommended", pattern="^(recommended|mandatory)$")
    due_date: datetime | None = None
    publication_id: str | None = None


class SbOut(BaseModel):
    id: str
    organization_id: str
    sb_number: str
    sb_type: str
    manufacturer: str
    revision: str
    title: str
    applicability: str
    priority: str
    compliance_status: str
    due_date: datetime | None
    completed_at: datetime | None
    publication_id: str | None
    linked_work_order_id: str | None
    history_notes: str
    created_at: datetime
    updated_at: datetime


class EoCreate(BaseModel):
    organization_id: str | None = None
    eo_number: str = Field(min_length=1, max_length=80)
    revision: str = "0"
    title: str = Field(min_length=1, max_length=300)
    effectivity: str = ""
    work_instructions: str = ""
    references: str = ""
    publication_id: str | None = None
    due_date: datetime | None = None


class EoOut(BaseModel):
    id: str
    organization_id: str
    eo_number: str
    revision: str
    title: str
    status: str
    effectivity: str
    work_instructions: str
    references: str
    publication_id: str | None
    approved_by: str
    approved_at: datetime | None
    linked_work_order_id: str | None
    due_date: datetime | None
    history_notes: str
    created_at: datetime
    updated_at: datetime


class DefectCreate(BaseModel):
    organization_id: str | None = None
    aircraft_id: str
    defect_number: str | None = None
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    deferral_type: str = Field(default="mel", pattern="^(mel|cdl|other)$")
    mel_item_id: str | None = None
    dispatch_category: str = Field(default="", pattern="^$|^[ABCD]$")
    repair_interval_hours: Decimal | None = None
    repair_interval_days: int | None = None
    expires_at: datetime | None = None
    ata_chapter_id: str | None = None


class DefectOut(BaseModel):
    id: str
    organization_id: str
    aircraft_id: str
    defect_number: str
    title: str
    description: str
    status: str
    deferral_type: str
    mel_item_id: str | None
    dispatch_category: str
    repair_interval_hours: Decimal | None
    repair_interval_days: int | None
    expires_at: datetime | None
    ata_chapter_id: str | None
    linked_work_order_id: str | None
    alert_level: str
    created_at: datetime
    updated_at: datetime


class MelItemCreate(BaseModel):
    organization_id: str | None = None
    list_type: str = Field(default="mel", pattern="^(mel|cdl)$")
    item_number: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    ata_chapter_id: str | None = None
    dispatch_category: str = Field(default="C", pattern="^[ABCD]$")
    repair_interval_days: int | None = None
    repair_interval_hours: Decimal | None = None
    dispatch_restrictions: str = ""
    aircraft_model_id: str | None = None


class MelItemOut(BaseModel):
    id: str
    organization_id: str
    list_type: str
    item_number: str
    title: str
    ata_chapter_id: str | None
    dispatch_category: str
    repair_interval_days: int | None
    repair_interval_hours: Decimal | None
    dispatch_restrictions: str
    aircraft_model_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class UtilizationUpsert(BaseModel):
    organization_id: str | None = None
    aircraft_id: str
    location: str = ""
    ops_status: str = Field(default="available", pattern="^(available|grounded|maintenance|ferry)$")
    flight_hours: Decimal | None = Field(default=None, ge=0)
    flight_cycles: int | None = Field(default=None, ge=0)
    landings: int | None = Field(default=None, ge=0)
    engine_hours: Decimal | None = Field(default=None, ge=0)
    apu_hours: Decimal | None = Field(default=None, ge=0)


class UtilizationOut(BaseModel):
    id: str
    organization_id: str
    aircraft_id: str
    location: str
    ops_status: str
    flight_hours: Decimal
    flight_cycles: int
    landings: int
    engine_hours: Decimal
    apu_hours: Decimal
    traffic_light: str
    updated_at: datetime


class HangarPlanCreate(BaseModel):
    organization_id: str | None = None
    aircraft_id: str
    work_package_id: str | None = None
    hangar: str = ""
    bay: str = ""
    team_name: str = ""
    supervisor_employee_id: str | None = None
    shift_code: str = ""
    estimated_duration_hours: Decimal = Field(default=Decimal("0.00"), ge=0)
    critical_path: bool = False
    capacity_note: str = ""
    scheduled_start: datetime | None = None
    scheduled_finish: datetime | None = None


class HangarPlanOut(BaseModel):
    id: str
    organization_id: str
    aircraft_id: str
    work_package_id: str | None
    hangar: str
    bay: str
    team_name: str
    supervisor_employee_id: str | None
    shift_code: str
    estimated_duration_hours: Decimal
    critical_path: bool
    capacity_note: str
    scheduled_start: datetime | None
    scheduled_finish: datetime | None
    status: str
    created_at: datetime


class ForecastItemOut(BaseModel):
    source_type: str
    source_id: str
    aircraft_id: str | None
    title: str
    due_basis: str
    due_at: datetime | None
    due_hours: Decimal | None
    due_cycles: int | None
    urgency: str  # overdue | due_soon | future
    days_remaining: int | None
    hours_remaining: Decimal | None
    cycles_remaining: int | None


class ForecastOut(BaseModel):
    horizon_days: int
    generated_at: datetime
    overdue: list[ForecastItemOut]
    due_soon: list[ForecastItemOut]
    future: list[ForecastItemOut]
    by_flight_hours: list[ForecastItemOut]
    by_flight_cycles: list[ForecastItemOut]


class DueListOut(BaseModel):
    generated_at: datetime
    items: list[ForecastItemOut]


class PlannerDashboardOut(BaseModel):
    aircraft_count: int
    grounded: int
    available: int
    checks_due: int
    ads_due: int
    sbs_due: int
    eos_due: int
    deferred_defects: int
    waiting_parts: int
    waiting_engineering: int
    waiting_inspection: int
    waiting_aca: int
    traffic_lights: dict[str, int]


class AircraftStatusOut(BaseModel):
    aircraft_id: str
    registration: str
    operator: str
    fleet_id: str | None
    location: str
    ops_status: str
    flight_hours: Decimal
    flight_cycles: int
    engine_hours: Decimal
    apu_hours: Decimal
    open_defects: int
    deferred_defects: int
    upcoming_checks: int
    traffic_light: str
    maintenance_status: str


class GeneratePackageRequest(BaseModel):
    check_id: str
    include_mpd_tasks: bool = True
    max_job_cards: int = Field(default=20, ge=1, le=100)


class GeneratePackageOut(BaseModel):
    work_package_id: str
    package_number: str
    work_order_ids: list[str]
    job_card_ids: list[str]
    check_id: str


class WorkforcePlanLineCreate(BaseModel):
    organization_id: str | None = None
    work_package_id: str | None = None
    employee_id: str = Field(min_length=1, max_length=80)
    role_code: str = Field(pattern="^(technician|inspector|ii|aca|engineer|stores)$")
    shift_code: str = ""
    license_ok: bool = True
    authorization_ok: bool = True
    available: bool = True
    workload_hours: Decimal = Field(default=Decimal("0.00"), ge=0)
    status: str = Field(default="assigned", pattern="^(planned|assigned|released|complete|cancelled)$")


class WorkforcePlanLineUpdate(BaseModel):
    work_package_id: str | None = None
    role_code: str | None = Field(default=None, pattern="^(technician|inspector|ii|aca|engineer|stores)$")
    shift_code: str | None = None
    license_ok: bool | None = None
    authorization_ok: bool | None = None
    available: bool | None = None
    workload_hours: Decimal | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, pattern="^(planned|assigned|released|complete|cancelled)$")


class WorkforcePlanLineOut(BaseModel):
    id: str
    organization_id: str
    work_package_id: str | None
    employee_id: str
    role_code: str
    shift_code: str
    license_ok: bool
    authorization_ok: bool
    available: bool
    workload_hours: Decimal
    status: str
    created_at: datetime
