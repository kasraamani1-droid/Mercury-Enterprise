"""Program 17 — Event Fabric schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


class EventTypeOut(BaseModel):
    model_config = ORM

    id: str
    code: str
    family: str
    version: str
    description: str
    severity_default: str
    ai_ready: str
    status: str


class PublishEventIn(BaseModel):
    organization_id: str | None = None
    event_code: str = Field(min_length=1, max_length=120)
    event_version: str = "1.0"
    payload_json: str = "{}"
    actor: str = ""
    source_service: str = "mercury"
    target_service: str = ""
    correlation_id: str = ""
    trace_id: str = ""
    severity: str = ""
    duration_ms: int = 0
    bus_event_type: str = ""


class StoredEventOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    event_id: str
    event_code: str
    event_version: str
    family: str
    bus_event_type: str
    payload_json: str
    actor: str
    source_service: str
    target_service: str
    correlation_id: str
    trace_id: str
    severity: str
    status: str
    duration_ms: int
    occurred_at: datetime
    created_at: datetime


class SubscriptionCreate(BaseModel):
    organization_id: str | None = None
    event_code: str = "*"
    subscriber_name: str = Field(min_length=1, max_length=200)
    filter_json: str = "{}"
    endpoint_hint: str = ""


class SubscriptionOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    event_code: str
    subscriber_name: str
    filter_json: str
    endpoint_hint: str
    status: str
    created_by: str
    created_at: datetime


class DeadLetterOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    store_event_id: str
    event_code: str
    subscriber_name: str
    error_message: str
    retry_count: int
    status: str
    created_at: datetime


class ReplayRequest(BaseModel):
    organization_id: str | None = None
    event_code: str = ""
    from_occurred_at: datetime | None = None
    to_occurred_at: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)


class ReplayOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    event_code: str
    events_replayed: int
    status: str
    created_by: str
    created_at: datetime


class EventFabricOverviewOut(BaseModel):
    organization_id: str
    catalog_types: int
    stored_events: int
    subscriptions: int
    dead_letters_open: int
    replays: int
    families: dict[str, int]
    disclaimer: str
