"""Connect schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


class ConnectorOut(BaseModel):
    model_config = ORM

    id: str
    code: str
    name: str
    category: str
    description: str
    capabilities_json: str
    auth_modes_json: str
    direction: str
    readiness: str
    status: str


class BindingCreate(BaseModel):
    organization_id: str | None = None
    connector_code: str = Field(min_length=1, max_length=80)
    display_name: str = ""
    config_ref: str = ""
    endpoint_hint: str = ""
    metadata_json: str = "{}"


class BindingOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    connector_code: str
    display_name: str
    binding_status: str
    config_ref: str
    endpoint_hint: str
    metadata_json: str
    created_at: datetime


class ConnectOverviewOut(BaseModel):
    organization_id: str
    connectors: int
    bindings: int
    by_category: dict[str, int]
    readiness: dict[str, int]
