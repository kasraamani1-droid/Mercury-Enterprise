"""Program 14 — Aviation Network schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


class OrgProfileCreate(BaseModel):
    organization_id: str | None = None
    org_type: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=300)
    summary: str = ""
    capabilities_json: str = "[]"
    certificates_json: str = "[]"
    approvals_json: str = "[]"
    facilities_json: str = "[]"
    locations_json: str = "[]"
    aircraft_supported_json: str = "[]"
    engines_supported_json: str = "[]"
    ratings_json: str = "[]"
    marketplace_profile_ref: str = ""
    careers_json: str = "{}"
    training_json: str = "{}"
    library_access_json: str = "{}"
    directory_visible: bool = True


class OrgProfileOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    org_type: str
    display_name: str
    summary: str
    capabilities_json: str
    certificates_json: str
    approvals_json: str
    facilities_json: str
    locations_json: str
    aircraft_supported_json: str
    engines_supported_json: str
    ratings_json: str
    marketplace_profile_ref: str
    directory_visible: str
    status: str
    created_at: datetime


class ProfessionalCreate(BaseModel):
    organization_id: str | None = None
    professional_role: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=200)
    headline: str = ""
    experience_json: str = "[]"
    licenses_json: str = "[]"
    ratings_json: str = "[]"
    training_json: str = "[]"
    certificates_json: str = "[]"
    skills_json: str = "[]"
    employment_history_json: str = "[]"
    portfolio_json: str = "[]"
    credential_links_json: str = "[]"
    personnel_ref: str = ""
    directory_visible: bool = False


class ProfessionalOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    username: str
    professional_role: str
    display_name: str
    headline: str
    licenses_json: str
    skills_json: str
    directory_visible: str
    status: str
    created_at: datetime


class PartnershipCreate(BaseModel):
    organization_id: str | None = None
    partner_organization_id: str = Field(min_length=1, max_length=80)
    partnership_type: str = Field(min_length=1, max_length=80)
    permissions_json: str = '["messaging","document_share","collaboration"]'
    contracts_json: str = "[]"
    notes: str = ""
    expires_at: datetime | None = None


class PartnershipOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    partner_organization_id: str
    partnership_type: str
    status: str
    permissions_json: str
    contracts_json: str
    expires_at: datetime | None
    notes: str
    created_by: str
    approved_by: str
    created_at: datetime


class PartnershipApprove(BaseModel):
    organization_id: str | None = None


class CollaborationCreate(BaseModel):
    organization_id: str | None = None
    partner_organization_id: str
    partnership_id: str = ""
    collaboration_type: str
    title: str = Field(min_length=1, max_length=300)
    summary: str = ""
    work_package_ref: str = ""
    project_ref: str = ""
    metadata_json: str = "{}"


class CollaborationOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    partner_organization_id: str
    partnership_id: str
    collaboration_type: str
    title: str
    summary: str
    status: str
    work_package_ref: str
    project_ref: str
    created_by: str
    created_at: datetime


class DocumentShareCreate(BaseModel):
    organization_id: str | None = None
    partner_organization_id: str
    partnership_id: str = ""
    document_ref: str = Field(min_length=1, max_length=200)
    title: str = ""
    share_mode: str = "read_only"
    watermark: bool = True
    download_allowed: bool = False
    approval_required: bool = False
    expires_at: datetime | None = None


class DocumentShareOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    partner_organization_id: str
    partnership_id: str
    document_ref: str
    title: str
    share_mode: str
    watermark: str
    download_allowed: str
    approval_required: str
    approval_status: str
    expires_at: datetime | None
    status: str
    created_by: str
    created_at: datetime


class ThreadCreate(BaseModel):
    organization_id: str | None = None
    partner_organization_id: str = ""
    scope: str = "org_to_org"
    subject: str = Field(min_length=1, max_length=300)
    project_ref: str = ""
    work_package_ref: str = ""
    marketplace_ref: str = ""
    partnership_id: str = ""


class ThreadOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    partner_organization_id: str
    scope: str
    subject: str
    project_ref: str
    work_package_ref: str
    marketplace_ref: str
    partnership_id: str
    status: str
    created_by: str
    created_at: datetime


class MessageCreate(BaseModel):
    organization_id: str | None = None
    thread_id: str
    body: str = Field(min_length=1)


class MessageOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    thread_id: str
    sender_username: str
    body: str
    created_at: datetime


class EventCreate(BaseModel):
    organization_id: str | None = None
    event_type: str
    title: str = Field(min_length=1, max_length=300)
    summary: str = ""
    location: str = ""
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    directory_visible: bool = True
    metadata_json: str = "{}"


class EventOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    event_type: str
    title: str
    summary: str
    location: str
    starts_at: datetime | None
    ends_at: datetime | None
    directory_visible: str
    status: str
    created_at: datetime


class DirectoryHitOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    entity_type: str
    entity_ref: str
    title: str
    summary: str
    tags_json: str
    visibility: str
    status: str


class DirectorySearchResponse(BaseModel):
    query: str
    total: int
    items: list[DirectoryHitOut]


class NetworkOverviewOut(BaseModel):
    organization_id: str
    org_profiles: int
    professionals: int
    partnerships: int
    collaborations: int
    document_shares: int
    threads: int
    events: int
    directory_entries: int
    disclaimer: str
