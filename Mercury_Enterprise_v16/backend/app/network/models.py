"""Program 14 — Mercury Aviation Network data model.

Enterprise aviation collaboration network. Tenant isolation by default;
cross-organization access only through explicit partnerships and approvals.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


class NetworkOrgProfile(Base):
    """Public/network-facing organization profile (still tenant-owned)."""

    __tablename__ = "network_org_profiles"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    org_type: Mapped[str] = mapped_column(String(80), index=True)
    display_name: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, default="")
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    certificates_json: Mapped[str] = mapped_column(Text, default="[]")
    approvals_json: Mapped[str] = mapped_column(Text, default="[]")
    facilities_json: Mapped[str] = mapped_column(Text, default="[]")
    locations_json: Mapped[str] = mapped_column(Text, default="[]")
    aircraft_supported_json: Mapped[str] = mapped_column(Text, default="[]")
    engines_supported_json: Mapped[str] = mapped_column(Text, default="[]")
    ratings_json: Mapped[str] = mapped_column(Text, default="[]")
    marketplace_profile_ref: Mapped[str] = mapped_column(String(80), default="")
    careers_json: Mapped[str] = mapped_column(Text, default="{}")
    training_json: Mapped[str] = mapped_column(Text, default="{}")
    library_access_json: Mapped[str] = mapped_column(Text, default="{}")
    directory_visible: Mapped[str] = mapped_column(String(10), default="true", index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "org_type", name="uq_network_org_profile"),
        Index("ix_network_org_type_status", "org_type", "status"),
    )


class NetworkProfessionalProfile(Base):
    """Professional aviation profile — not a social profile."""

    __tablename__ = "network_professional_profiles"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    professional_role: Mapped[str] = mapped_column(String(80), index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    headline: Mapped[str] = mapped_column(String(300), default="")
    experience_json: Mapped[str] = mapped_column(Text, default="[]")
    licenses_json: Mapped[str] = mapped_column(Text, default="[]")
    ratings_json: Mapped[str] = mapped_column(Text, default="[]")
    training_json: Mapped[str] = mapped_column(Text, default="[]")
    certificates_json: Mapped[str] = mapped_column(Text, default="[]")
    skills_json: Mapped[str] = mapped_column(Text, default="[]")
    employment_history_json: Mapped[str] = mapped_column(Text, default="[]")
    portfolio_json: Mapped[str] = mapped_column(Text, default="[]")
    credential_links_json: Mapped[str] = mapped_column(Text, default="[]")
    personnel_ref: Mapped[str] = mapped_column(String(80), default="")
    directory_visible: Mapped[str] = mapped_column(String(10), default="false", index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "username", "professional_role", name="uq_network_prof"
        ),
        Index("ix_network_prof_role", "professional_role", "status"),
    )


class NetworkPartnership(Base):
    """Explicit cross-organization relationship — required for collaboration."""

    __tablename__ = "network_partnerships"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)  # initiating / home org
    partner_organization_id: Mapped[str] = mapped_column(String(80), index=True)
    partnership_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="proposed", index=True)
    permissions_json: Mapped[str] = mapped_column(Text, default="[]")
    contracts_json: Mapped[str] = mapped_column(Text, default="[]")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "partner_organization_id",
            "partnership_type",
            name="uq_network_partnership",
        ),
        Index("ix_network_partner_status", "organization_id", "status"),
    )


class NetworkCollaboration(Base):
    """Authorized collaboration request / shared project between orgs."""

    __tablename__ = "network_collaborations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)  # requester
    partner_organization_id: Mapped[str] = mapped_column(String(80), index=True)
    partnership_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    collaboration_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="requested", index=True)
    work_package_ref: Mapped[str] = mapped_column(String(80), default="")
    project_ref: Mapped[str] = mapped_column(String(80), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_network_collab_org_status", "organization_id", "status"),)


class NetworkDocumentShare(Base):
    """Controlled document sharing with expiry, mode, and audit trail."""

    __tablename__ = "network_document_shares"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)  # owner
    partner_organization_id: Mapped[str] = mapped_column(String(80), index=True)
    partnership_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    document_ref: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300), default="")
    share_mode: Mapped[str] = mapped_column(String(40), default="read_only")
    watermark: Mapped[str] = mapped_column(String(10), default="true")
    download_allowed: Mapped[str] = mapped_column(String(10), default="false")
    approval_required: Mapped[str] = mapped_column(String(10), default="false")
    approval_status: Mapped[str] = mapped_column(String(40), default="not_required")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_network_doc_share_org", "organization_id", "status"),)


class NetworkMessageThread(Base):
    __tablename__ = "network_message_threads"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    partner_organization_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    scope: Mapped[str] = mapped_column(String(40), index=True)
    subject: Mapped[str] = mapped_column(String(300))
    project_ref: Mapped[str] = mapped_column(String(80), default="")
    work_package_ref: Mapped[str] = mapped_column(String(80), default="")
    marketplace_ref: Mapped[str] = mapped_column(String(80), default="")
    partnership_id: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_network_thread_scope", "organization_id", "scope"),)


class NetworkMessage(Base):
    __tablename__ = "network_messages"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    thread_id: Mapped[str] = mapped_column(String(80), index=True)
    sender_username: Mapped[str] = mapped_column(String(120), index=True)
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_network_msg_thread", "thread_id", "created_at"),)


class NetworkEvent(Base):
    __tablename__ = "network_events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(300), default="")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    directory_visible: Mapped[str] = mapped_column(String(10), default="true")
    status: Mapped[str] = mapped_column(String(40), default="published", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_network_event_type", "event_type", "status"),)


class NetworkDirectoryEntry(Base):
    """Searchable directory projection — opt-in visibility only."""

    __tablename__ = "network_directory_entries"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_ref: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(400))
    summary: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    visibility: Mapped[str] = mapped_column(String(40), default="network", index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "entity_type", "entity_ref", name="uq_network_dir"),
        Index("ix_network_dir_search", "entity_type", "status"),
    )
