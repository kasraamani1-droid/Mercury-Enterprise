"""Program 16 — Plugin schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


class PluginOut(BaseModel):
    model_config = ORM

    id: str
    code: str
    name: str
    category: str
    connect_connector: str
    description: str
    capabilities_json: str
    readiness: str
    disclaimer: str
    status: str
    created_at: datetime


class InstallationCreate(BaseModel):
    organization_id: str | None = None
    plugin_code: str = Field(min_length=1, max_length=80)
    install_status: str = "installed"
    config_json: str = "{}"
    config_ref: str = ""
    notes: str = ""


class InstallationOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    plugin_code: str
    install_status: str
    connect_binding_id: str
    config_json: str
    config_ref: str
    notes: str
    created_by: str
    created_at: datetime


class DashboardCreate(BaseModel):
    organization_id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    widgets_json: str = "[]"
    is_default: bool = False


class DashboardOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    name: str
    widgets_json: str
    is_default: str
    status: str
    created_by: str
    created_at: datetime


class PluginsOverviewOut(BaseModel):
    organization_id: str
    plugins: int
    installations: int
    dashboards: int
    by_category: dict[str, int]
    by_readiness: dict[str, int]
    disclaimer: str
