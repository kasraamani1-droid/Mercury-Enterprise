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

class EvidenceOut(EvidenceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    incident_id: str
    created_at: datetime

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

class IncidentDetail(IncidentOut):
    events: list[TimelineEventOut]
    evidence: list[EvidenceOut]


class IncidentStatusUpdate(BaseModel):
    status: str
    approval_id: str | None = None