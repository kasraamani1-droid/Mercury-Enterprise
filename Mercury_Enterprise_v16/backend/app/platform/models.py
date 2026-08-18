"""Program A — Enterprise Platform Foundation data model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Identity — API keys, PATs, MFA enrollment (ready)
# ---------------------------------------------------------------------------


class PlatformApiKey(Base):
    """Machine credential scoped to an organization."""

    __tablename__ = "platform_api_keys"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    key_prefix: Mapped[str] = mapped_column(String(16), index=True)
    key_hash: Mapped[str] = mapped_column(String(128))
    scopes: Mapped[str] = mapped_column(Text, default="")  # comma-separated permissions
    created_by: Mapped[str] = mapped_column(String(120), default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_plat_apikey_org_status", "organization_id", "status"),)


class PlatformPersonalAccessToken(Base):
    """User-scoped PAT for automation."""

    __tablename__ = "platform_pats"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(200))
    token_prefix: Mapped[str] = mapped_column(String(16), index=True)
    token_hash: Mapped[str] = mapped_column(String(128))
    scopes: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PlatformMfaEnrollment(Base):
    """MFA enrollment record (TOTP secret stored hashed/encrypted at rest later)."""

    __tablename__ = "platform_mfa_enrollments"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    method: Mapped[str] = mapped_column(String(40), default="totp")  # totp | webauthn
    secret_ref: Mapped[str] = mapped_column(String(200), default="")  # vault/ref — never raw in API
    enabled: Mapped[str] = mapped_column(String(10), default="false")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ---------------------------------------------------------------------------
# Organization extensions — facilities, BUs, cost centers, hangars, stations
# ---------------------------------------------------------------------------


class PlatformBusinessUnit(Base):
    __tablename__ = "platform_business_units"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    country_code: Mapped[str] = mapped_column(String(8), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_plat_bu_code"),)


class PlatformCostCenter(Base):
    __tablename__ = "platform_cost_centers"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    business_unit_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_plat_cc_code"),)


class PlatformFacility(Base):
    """Physical facility: hangar, shop, station, warehouse building, office."""

    __tablename__ = "platform_facilities"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    site_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    # hangar | shop | station | warehouse | office | other
    facility_type: Mapped[str] = mapped_column(String(40), default="hangar", index=True)
    country_code: Mapped[str] = mapped_column(String(8), default="")
    address: Mapped[str] = mapped_column(String(400), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_plat_fac_code"),)


# ---------------------------------------------------------------------------
# RBAC extensions — templates, custom roles, temp access, permission audit
# ---------------------------------------------------------------------------


class PlatformRoleTemplate(Base):
    __tablename__ = "platform_role_templates"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    permissions: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    # system | aviation | custom
    template_type: Mapped[str] = mapped_column(String(40), default="aviation", index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PlatformCustomRole(Base):
    __tablename__ = "platform_custom_roles"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    permissions: Mapped[str] = mapped_column(Text, default="")
    template_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_plat_custom_role"),)


class PlatformTemporaryAccess(Base):
    __tablename__ = "platform_temporary_access"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    permissions: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_plat_temp_org_user", "organization_id", "username", "status"),)


class PlatformPermissionAudit(Base):
    """Dedicated permission-change ledger (also mirrored to global audit)."""

    __tablename__ = "platform_permission_audits"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(120), index=True)
    target_username: Mapped[str] = mapped_column(String(120), default="", index=True)
    change_type: Mapped[str] = mapped_column(String(40), index=True)  # grant | revoke | role | temp
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ---------------------------------------------------------------------------
# Workflow engine — generic, no domain hardcoding
# ---------------------------------------------------------------------------


class PlatformWorkflowDefinition(Base):
    __tablename__ = "platform_workflow_definitions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    # JSON-ish states/transitions stored as text for designer-ready future UI
    states_json: Mapped[str] = mapped_column(Text, default="")
    transitions_json: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "code", "version", name="uq_plat_wf_ver"),)


class PlatformWorkflowInstance(Base):
    __tablename__ = "platform_workflow_instances"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    definition_id: Mapped[str] = mapped_column(ForeignKey("platform_workflow_definitions.id"), index=True)
    # Polymorphic binding to any domain entity
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    current_state: Mapped[str] = mapped_column(String(40), index=True)
    assigned_to: Mapped[str] = mapped_column(String(120), default="")
    # draft | assigned | in_progress | waiting | inspection | rejected | released | archived
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_plat_wf_inst_entity", "organization_id", "entity_type", "entity_id"),
    )


class PlatformWorkflowTransitionLog(Base):
    __tablename__ = "platform_workflow_transition_logs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    instance_id: Mapped[str] = mapped_column(ForeignKey("platform_workflow_instances.id"), index=True)
    from_state: Mapped[str] = mapped_column(String(40), default="")
    to_state: Mapped[str] = mapped_column(String(40))
    performed_by: Mapped[str] = mapped_column(String(120), default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ---------------------------------------------------------------------------
# Notifications — event-driven multi-channel
# ---------------------------------------------------------------------------


class PlatformNotification(Base):
    __tablename__ = "platform_notifications"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    recipient: Mapped[str] = mapped_column(String(200), index=True)
    # email | sms | push | in_app | slack | teams | webhook
    channel: Mapped[str] = mapped_column(String(40), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    # pending | sent | failed | read
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    error_detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_plat_notif_org_status", "organization_id", "status"),)


# ---------------------------------------------------------------------------
# Files — versioned metadata (blob via storage backend interface)
# ---------------------------------------------------------------------------


class PlatformFileObject(Base):
    __tablename__ = "platform_file_objects"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    # pdf | image | cad | office | publication | other
    file_class: Mapped[str] = mapped_column(String(40), default="other", index=True)
    storage_uri: Mapped[str] = mapped_column(String(500), default="")
    sha256: Mapped[str] = mapped_column(String(64), default="", index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    # pending_scan | clean | infected | skipped
    virus_scan_status: Mapped[str] = mapped_column(String(40), default="skipped", index=True)
    entity_type: Mapped[str] = mapped_column(String(80), default="", index=True)
    entity_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    uploaded_by: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_plat_file_org_entity", "organization_id", "entity_type", "entity_id"),
    )


# ---------------------------------------------------------------------------
# Search — indexed documents for global enterprise search
# ---------------------------------------------------------------------------


class PlatformSearchDocument(Base):
    __tablename__ = "platform_search_documents"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    # aircraft | component | personnel | organization | work_order | publication | marketplace | career | other
    doc_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(400), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    # AI readiness metadata (JSON) — searchable/embedding flags; no LLM calls
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "doc_type", "entity_id", name="uq_plat_search_doc"),
        Index("ix_plat_search_org_type", "organization_id", "doc_type"),
    )


# ---------------------------------------------------------------------------
# Configuration — settings, feature flags, licensing
# ---------------------------------------------------------------------------


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)  # "*" for system
    key: Mapped[str] = mapped_column(String(120), index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    # system | organization | feature_flag | license | regional
    category: Mapped[str] = mapped_column(String(40), default="organization", index=True)
    updated_by: Mapped[str] = mapped_column(String(120), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "key", name="uq_plat_setting"),)


class PlatformFeatureFlag(Base):
    __tablename__ = "platform_feature_flags"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(400), default="")
    enabled_global: Mapped[str] = mapped_column(String(10), default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PlatformOrgFeatureFlag(Base):
    __tablename__ = "platform_org_feature_flags"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    flag_code: Mapped[str] = mapped_column(String(80), index=True)
    enabled: Mapped[str] = mapped_column(String(10), default="true")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "flag_code", name="uq_plat_org_flag"),)
