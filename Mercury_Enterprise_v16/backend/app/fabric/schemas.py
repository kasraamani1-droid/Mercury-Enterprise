"""Program 11 — Universal Data Fabric schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


class EntityTypeOut(BaseModel):
    model_config = ORM

    id: str
    code: str
    name: str
    domain: str
    description: str
    passport_kind: str
    searchable: str
    ai_ready: str
    status: str


class PassportCreate(BaseModel):
    organization_id: str | None = None
    entity_type: str = Field(min_length=1, max_length=80)
    entity_id: str = Field(min_length=1, max_length=80)
    display_name: str = ""
    lifecycle: str = "active"
    ownership_json: str = "{}"
    tags_json: str = "[]"
    ai_metadata_json: str = "{}"
    permissions_hint: str = ""


class PassportOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    entity_type: str
    entity_id: str
    passport_number: str
    display_name: str
    lifecycle: str
    ownership_json: str
    digital_identity: str
    permissions_hint: str
    ai_metadata_json: str
    tags_json: str
    version: int
    status: str
    created_by: str
    created_at: datetime
    modified_at: datetime


class PassportHistoryOut(BaseModel):
    model_config = ORM

    id: str
    passport_id: str
    version: int
    change_type: str
    snapshot_json: str
    actor: str
    created_at: datetime


class RelationshipCreate(BaseModel):
    organization_id: str | None = None
    from_passport_id: str = Field(min_length=1)
    to_passport_id: str = Field(min_length=1)
    relationship_type: str = Field(min_length=1, max_length=80)
    cardinality: str = Field(default="many_to_many", pattern="^(one_to_one|one_to_many|many_to_many)$")
    cross_organization: bool = False
    target_organization_id: str = ""
    metadata_json: str = "{}"


class RelationshipOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    from_passport_id: str
    to_passport_id: str
    from_entity_type: str
    from_entity_id: str
    to_entity_type: str
    to_entity_id: str
    cardinality: str
    relationship_type: str
    cross_organization: str
    target_organization_id: str
    metadata_json: str
    status: str
    created_at: datetime


class EventCreate(BaseModel):
    organization_id: str | None = None
    passport_id: str = ""
    entity_type: str = Field(min_length=1, max_length=80)
    entity_id: str = Field(min_length=1, max_length=80)
    event_type: str = Field(min_length=1, max_length=80)
    title: str = ""
    details: str = ""
    correlation_id: str = ""
    payload_json: str = "{}"
    ai_metadata_json: str = "{}"
    occurred_at: datetime | None = None


class EventOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    passport_id: str
    entity_type: str
    entity_id: str
    event_type: str
    title: str
    details: str
    actor: str
    correlation_id: str
    payload_json: str
    ai_metadata_json: str
    occurred_at: datetime
    created_at: datetime


class TagCreate(BaseModel):
    organization_id: str | None = None
    passport_id: str
    tag: str = Field(min_length=1, max_length=120)
    category: str = "general"


class TagOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    passport_id: str
    tag: str
    category: str
    created_at: datetime


class AttachmentRefCreate(BaseModel):
    organization_id: str | None = None
    passport_id: str
    file_object_id: str
    role: str = "attachment"


class AttachmentRefOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    passport_id: str
    file_object_id: str
    role: str
    created_at: datetime


class RetentionPolicyOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    code: str
    name: str
    entity_type: str
    retention_days: int
    immutable: str
    archive_after_days: int
    description: str
    status: str


class LegalHoldCreate(BaseModel):
    organization_id: str | None = None
    passport_id: str
    reason: str = Field(min_length=1)


class LegalHoldOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    passport_id: str
    reason: str
    placed_by: str
    status: str
    placed_at: datetime
    released_at: datetime | None


class ThreadNodeOut(BaseModel):
    passport: PassportOut
    depth: int
    via_relationship: str = ""


class DigitalThreadOut(BaseModel):
    root_passport_id: str
    nodes: list[ThreadNodeOut]
    edges: list[RelationshipOut]


class FabricOverviewOut(BaseModel):
    organization_id: str
    entity_types: int
    passports: int
    relationships: int
    events: int
    tags: int
    legal_holds: int
    retention_policies: int


class FabricSearchHit(BaseModel):
    passport: PassportOut
    score: float = 1.0
