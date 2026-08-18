"""Program 15 — Digital Twin schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


class TwinCreate(BaseModel):
    organization_id: str | None = None
    twin_type: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=400)
    serial_number: str = ""
    part_number: str = ""
    fabric_entity_type: str = ""
    fabric_entity_id: str = ""
    lifecycle_state: str = "manufactured"
    ownership_json: str = "{}"
    ensure_passport: bool = True


class TwinOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    twin_uuid: str
    twin_type: str
    display_name: str
    serial_number: str
    part_number: str
    passport_id: str
    fabric_entity_type: str
    fabric_entity_id: str
    lifecycle_state: str
    ownership_json: str
    current_configuration_id: str
    utilization_json: str
    llp_json: str
    compliance_json: str
    certificates_json: str
    documents_json: str
    publications_json: str
    visualization_ready: str
    weight_balance_ready: str
    status: str
    ai_metadata_json: str
    created_at: datetime


class TwinDetailOut(TwinOut):
    history_count: int = 0
    configuration_count: int = 0
    reliability_count: int = 0
    disclaimer: str = ""


class LifecycleTransition(BaseModel):
    organization_id: str | None = None
    to_state: str
    summary: str = ""
    related_ref: str = ""


class HistoryCreate(BaseModel):
    organization_id: str | None = None
    history_kind: str
    title: str = ""
    summary: str = ""
    payload_json: str = "{}"
    related_ref: str = ""
    occurred_at: datetime | None = None


class HistoryOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    twin_id: str
    history_kind: str
    title: str
    summary: str
    payload_json: str
    related_ref: str
    fabric_event_id: str
    actor: str
    occurred_at: datetime
    created_at: datetime


class ConfigurationCreate(BaseModel):
    organization_id: str | None = None
    baseline: str = "current"
    version_label: str = ""
    configuration_json: str = "{}"
    engineering_changes_json: str = "[]"
    approved_modifications_json: str = "[]"
    optional_equipment_json: str = "[]"
    weight_balance_json: str = "{}"
    visualization_meta_json: str = "{}"
    set_as_current: bool = True


class ConfigurationOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    twin_id: str
    baseline: str
    version_label: str
    configuration_json: str
    engineering_changes_json: str
    approved_modifications_json: str
    optional_equipment_json: str
    weight_balance_json: str
    visualization_meta_json: str
    status: str
    created_at: datetime


class ReliabilityCreate(BaseModel):
    organization_id: str | None = None
    metric_code: str
    metric_value: str = ""
    unit: str = ""
    window_label: str = ""
    details_json: str = "{}"


class ReliabilityOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    twin_id: str
    metric_code: str
    metric_value: str
    unit: str
    window_label: str
    details_json: str
    architecture_only: str
    created_at: datetime


class RelationshipOut(BaseModel):
    twin_id: str
    passport_id: str
    fabric_relationships: list[dict]
    digital_thread_hint: str


class TwinSearchHit(BaseModel):
    model_config = ORM

    id: str
    twin_id: str
    twin_uuid: str
    twin_type: str
    passport_id: str
    serial_number: str
    title: str
    summary: str
    tags_json: str


class TwinSearchResponse(BaseModel):
    query: str
    total: int
    items: list[TwinSearchHit]


class TwinOverviewOut(BaseModel):
    organization_id: str
    twins: int
    by_type: dict[str, int]
    history_entries: int
    configurations: int
    reliability_snapshots: int
    disclaimer: str
