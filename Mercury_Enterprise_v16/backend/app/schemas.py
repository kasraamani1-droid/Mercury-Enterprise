from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class TimelineEventCreate(BaseModel):
    occurred_at: datetime
    event_type: str
    source: str
    description: str
    confidence: float = Field(ge=0, le=100)

class TimelineEventOut(TimelineEventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    incident_id: str

class EvidenceCreate(BaseModel):
    evidence_type: str
    source: str
    title: str
    content: str
    confidence: float = Field(ge=0, le=100)
    provenance: str | None = None

class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    incident_id: str
    evidence_type: str
    source: str
    title: str
    content: str
    confidence: float
    created_at: datetime
    provenance: str
    created_by: str
    organization_id: str | None = None
    site_id: str | None = None

class IncidentCreate(BaseModel):
    title: str
    status: str = "open"
    severity: str = "medium"
    summary: str = ""

class IncidentOut(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime
    organization_id: str | None = None
    site_id: str | None = None

class IncidentDetail(IncidentOut):
    events: list[TimelineEventOut]
    evidence: list[EvidenceOut]


class IncidentStatusUpdate(BaseModel):
    status: str
    approval_id: str | None = None


class OrganizationOut(BaseModel):
    organization_id: str
    name: str


class SiteOut(BaseModel):
    site_id: str
    organization_id: str
    name: str


class SessionContextUpdate(BaseModel):
    organization_id: str | None = None
    site_id: str | None = None


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    occurred_at: datetime
    action: str
    actor: str
    actor_role: str
    organization_id: str
    site_id: str
    target_type: str | None = None
    target_id: str | None = None
    source: str
    outcome: str
    origin: str
    details: str
