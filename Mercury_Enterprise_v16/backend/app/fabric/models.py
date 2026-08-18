"""Universal Data Fabric — relational substrate for the Digital Thread / Knowledge Graph."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Entity type catalog — canonical domain vocabulary
# ---------------------------------------------------------------------------


class FabricEntityType(Base):
    """Registered entity kinds in the Universal Entity Model."""

    __tablename__ = "fabric_entity_types"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(80), index=True)  # platform|aviation|logistics|…
    description: Mapped[str] = mapped_column(Text, default="")
    passport_kind: Mapped[str] = mapped_column(String(80), default="")  # aircraft|component|tool|…
    searchable: Mapped[str] = mapped_column(String(10), default="true")
    ai_ready: Mapped[str] = mapped_column(String(10), default="true")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ---------------------------------------------------------------------------
# Digital Passport — permanent digital identity for every object
# ---------------------------------------------------------------------------


class FabricPassport(Base):
    """Digital Passport: permanent identity linking a domain row into the thread."""

    __tablename__ = "fabric_passports"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)  # tenant
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)  # domain PK
    passport_number: Mapped[str] = mapped_column(String(120), index=True)
    display_name: Mapped[str] = mapped_column(String(400), default="")
    # draft | active | suspended | archived | retired
    lifecycle: Mapped[str] = mapped_column(String(40), default="active", index=True)
    ownership_json: Mapped[str] = mapped_column(Text, default="{}")
    digital_identity: Mapped[str] = mapped_column(String(200), default="")  # DID-style ref
    permissions_hint: Mapped[str] = mapped_column(Text, default="")  # comma perms for docs
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    modified_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "entity_type", "entity_id", name="uq_fabric_passport_entity"),
        UniqueConstraint("organization_id", "passport_number", name="uq_fabric_passport_number"),
        Index("ix_fabric_passport_org_type", "organization_id", "entity_type"),
        Index("ix_fabric_passport_lifecycle", "organization_id", "lifecycle"),
    )


class FabricPassportHistory(Base):
    """Immutable passport change history (revisions / ownership / lifecycle)."""

    __tablename__ = "fabric_passport_history"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    passport_id: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    change_type: Mapped[str] = mapped_column(String(40), index=True)  # create|update|lifecycle|ownership
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    actor: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_fabric_phist_passport", "passport_id", "version"),)


# ---------------------------------------------------------------------------
# Universal Relationship Engine
# ---------------------------------------------------------------------------


class FabricRelationship(Base):
    """Typed edges for 1:1, 1:N, M:N, cross-product, cross-org links."""

    __tablename__ = "fabric_relationships"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    # from / to are passport ids (preferred) with entity fallbacks for bootstrap
    from_passport_id: Mapped[str] = mapped_column(String(80), index=True)
    to_passport_id: Mapped[str] = mapped_column(String(80), index=True)
    from_entity_type: Mapped[str] = mapped_column(String(80), default="")
    from_entity_id: Mapped[str] = mapped_column(String(80), default="")
    to_entity_type: Mapped[str] = mapped_column(String(80), default="")
    to_entity_id: Mapped[str] = mapped_column(String(80), default="")
    # cardinality: one_to_one | one_to_many | many_to_many
    cardinality: Mapped[str] = mapped_column(String(40), default="many_to_many")
    # relationship_type examples: configured_as | installed_on | performed_on |
    # assigned_to | inspected_by | finding_of | supersedes | references | related_to
    relationship_type: Mapped[str] = mapped_column(String(80), index=True)
    cross_organization: Mapped[str] = mapped_column(String(10), default="false")
    target_organization_id: Mapped[str] = mapped_column(String(80), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_fabric_rel_from", "from_passport_id", "relationship_type"),
        Index("ix_fabric_rel_to", "to_passport_id", "relationship_type"),
        Index("ix_fabric_rel_org_type", "organization_id", "relationship_type"),
    )


# ---------------------------------------------------------------------------
# Fabric Event Model — enterprise timeline
# ---------------------------------------------------------------------------


class FabricEvent(Base):
    """Canonical enterprise event for the Digital Thread timeline."""

    __tablename__ = "fabric_events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    passport_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    # installed|removed|released|signed|approved|transferred|calibrated|
    # inspected|published|archived|cancelled|created|updated|…
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(120), default="")
    correlation_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        Index("ix_fabric_event_org_time", "organization_id", "occurred_at"),
        Index("ix_fabric_event_passport", "passport_id", "occurred_at"),
    )


# ---------------------------------------------------------------------------
# Tags & attachment refs
# ---------------------------------------------------------------------------


class FabricTag(Base):
    __tablename__ = "fabric_tags"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    passport_id: Mapped[str] = mapped_column(String(80), index=True)
    tag: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(80), default="general")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "passport_id", "tag", name="uq_fabric_tag"),
    )


class FabricAttachmentRef(Base):
    """Links a passport to a platform file object (no blob duplication)."""

    __tablename__ = "fabric_attachment_refs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    passport_id: Mapped[str] = mapped_column(String(80), index=True)
    file_object_id: Mapped[str] = mapped_column(String(80), index=True)
    role: Mapped[str] = mapped_column(String(80), default="attachment")  # certificate|photo|drawing|…
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Data governance
# ---------------------------------------------------------------------------


class FabricRetentionPolicy(Base):
    __tablename__ = "fabric_retention_policies"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)  # * = system
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str] = mapped_column(String(80), default="*", index=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=2555)  # ~7 years aviation-ish
    immutable: Mapped[str] = mapped_column(String(10), default="false")
    archive_after_days: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_fabric_retention"),)


class FabricLegalHold(Base):
    __tablename__ = "fabric_legal_holds"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    passport_id: Mapped[str] = mapped_column(String(80), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    placed_by: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)  # active|released
    placed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
