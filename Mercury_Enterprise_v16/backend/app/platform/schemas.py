"""Program A — Platform Foundation schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


class ApiKeyCreate(BaseModel):
    organization_id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    scopes: str = ""
    expires_at: datetime | None = None


class ApiKeyOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    name: str
    key_prefix: str
    scopes: str
    status: str
    created_by: str
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    secret: str | None = None


class PatCreate(BaseModel):
    organization_id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    scopes: str = ""
    expires_at: datetime | None = None


class PatOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    username: str
    name: str
    token_prefix: str
    scopes: str
    status: str
    expires_at: datetime | None
    created_at: datetime
    secret: str | None = None


class MfaEnrollRequest(BaseModel):
    method: str = Field(default="totp", pattern="^(totp|webauthn)$")


class MfaOut(BaseModel):
    model_config = ORM

    id: str
    username: str
    method: str
    enabled: str
    verified_at: datetime | None
    setup_ref: str = ""


class BusinessUnitCreate(BaseModel):
    organization_id: str | None = None
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    country_code: str = ""


class BusinessUnitOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    code: str
    name: str
    country_code: str
    status: str
    created_at: datetime


class CostCenterCreate(BaseModel):
    organization_id: str | None = None
    business_unit_id: str | None = None
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)


class CostCenterOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    business_unit_id: str | None
    code: str
    name: str
    status: str
    created_at: datetime


class FacilityCreate(BaseModel):
    organization_id: str | None = None
    site_id: str | None = None
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    facility_type: str = Field(
        default="hangar", pattern="^(hangar|shop|station|warehouse|office|other)$"
    )
    country_code: str = ""
    address: str = ""


class FacilityOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    site_id: str | None
    code: str
    name: str
    facility_type: str
    country_code: str
    address: str
    status: str
    created_at: datetime


class RoleTemplateOut(BaseModel):
    model_config = ORM

    id: str
    code: str
    name: str
    description: str
    permissions: str
    template_type: str
    status: str


class CustomRoleCreate(BaseModel):
    organization_id: str | None = None
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    permissions: str = Field(min_length=1)
    template_id: str | None = None


class CustomRoleOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    code: str
    name: str
    permissions: str
    template_id: str | None
    status: str
    created_by: str
    created_at: datetime


class TemporaryAccessCreate(BaseModel):
    organization_id: str | None = None
    username: str = Field(min_length=1, max_length=120)
    permissions: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    ends_at: datetime
    starts_at: datetime | None = None


class TemporaryAccessOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    username: str
    permissions: str
    reason: str
    approved_by: str
    starts_at: datetime
    ends_at: datetime
    status: str
    created_at: datetime


class PermissionAuditOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    actor: str
    target_username: str
    change_type: str
    details: str
    created_at: datetime


class WorkflowDefinitionCreate(BaseModel):
    organization_id: str | None = None
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    states_json: str = (
        '["draft","assigned","in_progress","waiting","inspection","rejected","released","archived"]'
    )
    transitions_json: str = "{}"


class WorkflowDefinitionOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    code: str
    name: str
    states_json: str
    transitions_json: str
    version: int
    status: str
    created_at: datetime


class WorkflowStartRequest(BaseModel):
    organization_id: str | None = None
    definition_code: str
    entity_type: str = Field(min_length=1, max_length=80)
    entity_id: str = Field(min_length=1, max_length=80)
    assigned_to: str = ""
    initial_state: str = "draft"


class WorkflowTransitionRequest(BaseModel):
    to_state: str = Field(min_length=1, max_length=40)
    comment: str = ""
    assigned_to: str | None = None


class WorkflowInstanceOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    definition_id: str
    entity_type: str
    entity_id: str
    current_state: str
    assigned_to: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class WorkflowTransitionLogOut(BaseModel):
    model_config = ORM

    id: str
    instance_id: str
    from_state: str
    to_state: str
    performed_by: str
    comment: str
    created_at: datetime


class NotificationCreate(BaseModel):
    organization_id: str | None = None
    recipient: str = Field(min_length=1, max_length=200)
    channel: str = Field(pattern="^(email|sms|push|in_app|slack|teams|webhook)$")
    event_type: str = Field(min_length=1, max_length=80)
    title: str = ""
    body: str = ""
    payload_json: str = "{}"


class NotificationOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    recipient: str
    channel: str
    event_type: str
    title: str
    body: str
    status: str
    created_at: datetime
    sent_at: datetime | None
    read_at: datetime | None


class FileRegisterRequest(BaseModel):
    organization_id: str | None = None
    filename: str = Field(min_length=1, max_length=300)
    content_type: str = "application/octet-stream"
    file_class: str = Field(
        default="other", pattern="^(pdf|image|cad|office|publication|other)$"
    )
    storage_uri: str = Field(min_length=1, max_length=500)
    sha256: str = ""
    size_bytes: int = Field(default=0, ge=0)
    entity_type: str = ""
    entity_id: str = ""
    virus_scan_status: str = Field(
        default="skipped", pattern="^(pending_scan|clean|infected|skipped)$"
    )


class FileUploadMeta(BaseModel):
    """Metadata fields for multipart upload (bytes supplied separately)."""

    organization_id: str | None = None
    file_class: str = Field(
        default="other", pattern="^(pdf|image|cad|office|publication|other)$"
    )
    entity_type: str = ""
    entity_id: str = ""
    virus_scan_status: str = Field(
        default="skipped", pattern="^(pending_scan|clean|infected|skipped)$"
    )


class FileObjectOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    filename: str
    content_type: str
    file_class: str
    storage_uri: str
    sha256: str
    size_bytes: int
    virus_scan_status: str
    entity_type: str
    entity_id: str
    version: int
    uploaded_by: str
    status: str
    created_at: datetime


class SearchIndexRequest(BaseModel):
    organization_id: str | None = None
    doc_type: str = Field(min_length=1, max_length=40)
    entity_id: str = Field(min_length=1, max_length=80)
    title: str = ""
    body: str = ""
    keywords: str = ""
    ai_metadata_json: str = "{}"


class SearchHitOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    doc_type: str
    entity_id: str
    title: str
    body: str
    keywords: str
    ai_metadata_json: str = "{}"
    updated_at: datetime


class SearchResponse(BaseModel):
    query: str
    total: int
    hits: list[SearchHitOut]


class SettingUpsert(BaseModel):
    organization_id: str | None = None
    key: str = Field(min_length=1, max_length=120)
    value: str = ""
    category: str = Field(
        default="organization",
        pattern="^(system|organization|feature_flag|license|regional)$",
    )


class SettingOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    key: str
    value: str
    category: str
    updated_by: str
    updated_at: datetime


class FeatureFlagOut(BaseModel):
    model_config = ORM

    id: str
    code: str
    description: str
    enabled_global: str


class OrgFeatureFlagSet(BaseModel):
    organization_id: str | None = None
    flag_code: str = Field(min_length=1, max_length=80)
    enabled: bool = True


class OrgFeatureFlagOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    flag_code: str
    enabled: str
    updated_at: datetime


class PlatformOverviewOut(BaseModel):
    organization_id: str
    api_keys: int
    pats: int
    facilities: int
    custom_roles: int
    workflow_definitions: int
    open_workflows: int
    pending_notifications: int
    files: int
    search_documents: int
    feature_flags_enabled: int


class PermissionMatrixOut(BaseModel):
    roles: dict[str, list[str]]
    templates: list[RoleTemplateOut]
