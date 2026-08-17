"""Ecosystem schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


class EcosystemOut(BaseModel):
    model_config = ORM

    id: str
    code: str
    name: str
    category: str
    description: str
    products_json: str
    ai_metadata_json: str
    status: str


class CapabilityOut(BaseModel):
    model_config = ORM

    id: str
    ecosystem_code: str
    code: str
    name: str
    description: str
    domain_refs_json: str
    fabric_entity_types_json: str
    readiness: str
    status: str


class EnrollmentCreate(BaseModel):
    organization_id: str | None = None
    ecosystem_code: str = Field(min_length=1, max_length=80)
    role_label: str = ""
    capabilities_enabled_json: str = "[]"


class EnrollmentOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    ecosystem_code: str
    role_label: str
    capabilities_enabled_json: str
    isolation_mode: str
    data_ownership: str
    status: str
    created_at: datetime


class EcosystemOverviewOut(BaseModel):
    organization_id: str
    ecosystems: int
    capabilities: int
    enrollments: int
    by_category: dict[str, int]
    readiness: dict[str, int]


class EcosystemDetailOut(BaseModel):
    ecosystem: EcosystemOut
    capabilities: list[CapabilityOut]
