from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class FaultCodeCreate(BaseModel):
    organization_id: str | None = None
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    ata_chapter_id: str | None = None
    status: str = "active"


class FaultCodeOut(BaseModel):
    id: str
    organization_id: str
    code: str
    title: str
    ata_chapter_id: str | None
    status: str
    created_at: datetime


class CriticalPolicyCreate(BaseModel):
    organization_id: str | None = None
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    domain: str = Field(
        pattern="^(engine|flight_controls|landing_gear|fuel|structural|propulsion|general)$"
    )
    requires_inspector: bool = True
    requires_independent: bool = False
    requires_aca: bool = True
    status: str = "active"


class CriticalPolicyOut(BaseModel):
    id: str
    organization_id: str
    code: str
    name: str
    domain: str
    requires_inspector: bool
    requires_independent: bool
    requires_aca: bool
    status: str
    created_at: datetime


TASK_TYPE_PATTERN = (
    "^(scheduled|unscheduled|corrective|preventive|inspection|functional_check|"
    "operational_check|troubleshooting|component_replacement|deferred_defect|"
    "mel_cdl|service_bulletin|engineering_order)$"
)


class TaskCreate(BaseModel):
    organization_id: str | None = None
    task_number: str | None = Field(default=None, max_length=80)
    task_type: str = Field(default="corrective", pattern=TASK_TYPE_PATTERN)
    aircraft_id: str = Field(min_length=1, max_length=80)
    ata_chapter_id: str | None = None
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    priority: str = Field(default="normal", pattern="^(low|normal|high|critical)$")
    due_date: datetime | None = None
    estimated_hours: Decimal = Field(default=Decimal("0.00"), ge=0)
    actual_hours: Decimal = Field(default=Decimal("0.00"), ge=0)
    publication_id: str | None = None
    publication_revision_id: str | None = None
    component_id: str | None = None
    serial_number: str = ""
    required_parts: str = ""
    required_tools: str = ""
    required_skills: str = ""
    required_certification: str = ""
    requires_inspector: bool | None = None
    independent_inspection_required: bool | None = None
    aca_required: bool | None = None
    fault_code_id: str | None = None
    critical_policy_id: str | None = None
    status: str = "open"
    performed_by_employee_id: str | None = None
    assigned_to_employee_id: str | None = None


class TaskOut(BaseModel):
    id: str
    organization_id: str
    task_number: str
    task_type: str
    aircraft_id: str
    fleet_id: str | None
    registration: str
    ata_chapter_id: str | None
    title: str
    description: str
    priority: str
    due_date: datetime | None
    estimated_hours: Decimal
    actual_hours: Decimal
    publication_id: str | None
    publication_revision_id: str | None
    component_id: str | None
    serial_number: str
    required_parts: str
    required_tools: str
    required_skills: str
    required_certification: str
    requires_inspector: bool
    independent_inspection_required: bool
    aca_required: bool
    fault_code_id: str | None
    critical_policy_id: str | None
    status: str
    release_status: str
    performed_by_employee_id: str | None
    assigned_to_employee_id: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class TaskTransitionRequest(BaseModel):
    to_status: str = Field(
        pattern=(
            "^(assigned|started|in_progress|paused|completed|closed|rejected|cancelled)$"
        )
    )
    assigned_to_employee_id: str | None = None
    notes: str = ""
    expected_version: int | None = None


class CertifyRequest(BaseModel):
    step: str = Field(
        pattern="^(performed|inspected|independent_inspection|aca_certified|aircraft_released)$"
    )
    employee_id: str = Field(min_length=1, max_length=80)
    method: str = Field(pattern="^(password|pin|pki|smart_card|biometric_ready)$")
    credential: str | None = None
    confirm_password: bool = False
    confirm_pin: bool = False
    notes: str = ""
    actual_hours: Decimal | None = Field(default=None, ge=0)
    expected_version: int | None = None


class CertificationEventOut(BaseModel):
    id: str
    organization_id: str
    task_id: str
    step: str
    actor_employee_id: str
    actor_username: str
    signature_id: str | None
    occurred_at: datetime
    notes: str


class DigitalSignatureOut(BaseModel):
    id: str
    organization_id: str
    signer_employee_id: str
    signer_username: str
    method: str
    purpose: str
    target_type: str
    target_id: str
    signature_hash: str
    pin_verified: str
    password_confirmed: str
    pki_ready: str
    smart_card_ready: str
    biometric_ready: str
    signed_at: datetime
    details: str


class CertifyOut(BaseModel):
    task: TaskOut
    signature: DigitalSignatureOut
    event: CertificationEventOut
    log_entry_id: str | None = None


class TechnicalLogOut(BaseModel):
    id: str
    organization_id: str
    aircraft_id: str
    registration: str
    ata_chapter_id: str | None
    task_id: str | None
    publication_id: str | None
    publication_revision_id: str | None
    component_id: str | None
    serial_number: str
    mechanic_employee_id: str | None
    inspector_employee_id: str | None
    independent_inspector_employee_id: str | None
    aca_employee_id: str | None
    release_signature_id: str | None
    summary: str
    occurred_at: datetime
    details: str


class LogbookAmendRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)
    summary: str = Field(default="", max_length=400)


class AiIndexStubCreate(BaseModel):
    organization_id: str | None = None
    source_type: str = Field(min_length=1, max_length=80)
    source_id: str = Field(min_length=1, max_length=80)
    title: str = ""
    ata_chapter_id: str | None = None


class AiIndexStubOut(BaseModel):
    id: str
    organization_id: str | None
    source_type: str
    source_id: str
    title: str
    ata_chapter_id: str | None
    status: str
    created_at: datetime


class AiCrossRefCreate(BaseModel):
    organization_id: str | None = None
    from_type: str = Field(min_length=1, max_length=80)
    from_id: str = Field(min_length=1, max_length=80)
    to_type: str = Field(min_length=1, max_length=80)
    to_id: str = Field(min_length=1, max_length=80)
    relation: str = Field(pattern="^(related_ata|related_component|related_task|related_fault)$")
    status: str = "active"


class AiCrossRefOut(BaseModel):
    id: str
    organization_id: str
    from_type: str
    from_id: str
    to_type: str
    to_id: str
    relation: str
    status: str
    created_at: datetime


class TaskAuditTrailOut(BaseModel):
    task: TaskOut
    certification_events: list[CertificationEventOut]
    signatures: list[DigitalSignatureOut]
    logbook_entries: list[TechnicalLogOut]
