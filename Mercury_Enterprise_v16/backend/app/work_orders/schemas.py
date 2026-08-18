from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

PRIORITY_PATTERN = "^(low|normal|high|critical)$"
JC_STATUS_PATTERN = (
    "^(draft|assigned|accepted|in_progress|paused|waiting_parts|waiting_engineering|"
    "waiting_inspection|completed|rejected|released|closed)$"
)


class WorkPackageCreate(BaseModel):
    organization_id: str | None = None
    package_number: str | None = Field(default=None, max_length=80)
    aircraft_id: str = Field(min_length=1, max_length=80)
    description: str = ""
    priority: str = Field(default="normal", pattern=PRIORITY_PATTERN)
    scheduled_start: datetime | None = None
    scheduled_finish: datetime | None = None
    planner_employee_id: str | None = None
    supervisor_employee_id: str | None = None
    hangar_bay: str = ""
    shift_code: str = ""
    estimated_hours: Decimal = Field(default=Decimal("0.00"), ge=0)


class WorkPackageOut(BaseModel):
    id: str
    organization_id: str
    package_number: str
    fleet_id: str | None
    aircraft_id: str
    registration: str
    description: str
    status: str
    priority: str
    scheduled_start: datetime | None
    scheduled_finish: datetime | None
    actual_start: datetime | None
    actual_finish: datetime | None
    planner_employee_id: str | None
    supervisor_employee_id: str | None
    hangar_bay: str
    shift_code: str
    estimated_hours: Decimal
    actual_hours: Decimal
    work_order_count: int = 0
    version: int
    created_at: datetime
    updated_at: datetime


class WorkOrderCreate(BaseModel):
    organization_id: str | None = None
    work_package_id: str = Field(min_length=1, max_length=80)
    wo_number: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    ata_chapter_id: str | None = None
    priority: str = Field(default="normal", pattern=PRIORITY_PATTERN)
    planner_employee_id: str | None = None
    supervisor_employee_id: str | None = None
    publication_id: str | None = None
    publication_revision_id: str | None = None
    due_date: datetime | None = None
    estimated_hours: Decimal = Field(default=Decimal("0.00"), ge=0)


class WorkOrderOut(BaseModel):
    id: str
    organization_id: str
    work_package_id: str
    wo_number: str
    aircraft_id: str
    ata_chapter_id: str | None
    title: str
    description: str
    status: str
    priority: str
    planner_employee_id: str | None
    supervisor_employee_id: str | None
    publication_id: str | None
    publication_revision_id: str | None
    due_date: datetime | None
    estimated_hours: Decimal
    actual_hours: Decimal
    job_card_count: int = 0
    version: int
    created_at: datetime
    updated_at: datetime


class JobCardCreate(BaseModel):
    organization_id: str | None = None
    work_order_id: str = Field(min_length=1, max_length=80)
    job_card_number: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    ata_chapter_id: str | None = None
    priority: str = Field(default="normal", pattern=PRIORITY_PATTERN)
    publication_id: str | None = None
    publication_revision_id: str | None = None
    component_id: str | None = None
    required_parts: str = ""
    required_tools: str = ""
    required_skills: str = ""
    required_certification: str = ""
    estimated_hours: Decimal = Field(default=Decimal("0.00"), ge=0)
    technician_employee_id: str | None = None
    hangar_bay: str = ""
    independent_inspection_required: bool = False
    aca_required: bool = True
    critical_policy_id: str | None = None


class JobCardOut(BaseModel):
    id: str
    organization_id: str
    work_order_id: str
    job_card_number: str
    maintenance_task_id: str | None
    aircraft_id: str
    ata_chapter_id: str | None
    title: str
    description: str
    status: str
    priority: str
    publication_id: str | None
    publication_revision_id: str | None
    component_id: str | None
    required_parts: str
    required_tools: str
    required_skills: str
    required_certification: str
    estimated_hours: Decimal
    actual_hours: Decimal
    technician_employee_id: str | None
    inspector_employee_id: str | None
    independent_inspector_employee_id: str | None
    aca_employee_id: str | None
    hangar_bay: str
    notes: str
    rework_reason: str
    independent_inspection_required: bool
    aca_required: bool
    version: int
    created_at: datetime
    updated_at: datetime


class JobCardTransitionRequest(BaseModel):
    to_status: str = Field(pattern=JC_STATUS_PATTERN)
    notes: str = ""
    actual_hours: Decimal | None = Field(default=None, ge=0)
    expected_version: int | None = None
    technician_employee_id: str | None = None


class JobCardAssignRequest(BaseModel):
    technician_employee_id: str = Field(min_length=1, max_length=80)
    hangar_bay: str = ""
    notes: str = ""
    expected_version: int | None = None


class JobCardAttachmentCreate(BaseModel):
    kind: str = Field(default="note", pattern="^(photo|note|document|drawing)$")
    title: str = ""
    storage_uri: str = ""
    content_type: str = ""
    notes: str = ""


class JobCardAttachmentOut(BaseModel):
    id: str
    organization_id: str
    job_card_id: str
    kind: str
    title: str
    storage_uri: str
    content_type: str
    notes: str
    created_by: str
    created_at: datetime


class JobCardCompleteWorkRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=80)
    method: str = Field(pattern="^(password|pin|pki|smart_card|biometric_ready)$")
    credential: str | None = None
    notes: str = ""
    actual_hours: Decimal | None = Field(default=None, ge=0)


class JobCardInspectRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=80)
    method: str = Field(pattern="^(password|pin|pki|smart_card|biometric_ready)$")
    credential: str | None = None
    decision: str = Field(pattern="^(approve|reject|rework|independent_inspection)$")
    notes: str = ""
    actual_hours: Decimal | None = Field(default=None, ge=0)


class JobCardReleaseRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=80)
    method: str = Field(pattern="^(password|pin|pki|smart_card|biometric_ready)$")
    credential: str | None = None
    notes: str = ""
    actual_hours: Decimal | None = Field(default=None, ge=0)


class ExecutionDashboardOut(BaseModel):
    role: str
    open_work_orders: int
    delayed_work_orders: int
    job_cards_by_status: dict[str, int]
    my_assigned_job_cards: int = 0
    awaiting_inspection: int = 0
    awaiting_release: int = 0
    released_today: int = 0


class ReportSummaryOut(BaseModel):
    report: str
    organization_id: str
    generated_at: datetime
    rows: list[dict]
