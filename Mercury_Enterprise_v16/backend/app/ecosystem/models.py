"""Aviation Digital Ecosystem data model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


class EcosystemDefinition(Base):
    """Top-level stakeholder ecosystem (Airline, MRO, CAMO, …)."""

    __tablename__ = "ecosystem_definitions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80), index=True)  # operator|provider|oem|authority|talent|commerce
    description: Mapped[str] = mapped_column(Text, default="")
    # Maps to Mercury products that serve this ecosystem
    products_json: Mapped[str] = mapped_column(Text, default="[]")
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class EcosystemCapability(Base):
    """Capability module inside an ecosystem (e.g. airline.fleet, mro.ndt)."""

    __tablename__ = "ecosystem_capabilities"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    ecosystem_code: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    # Links to existing Mercury domain packages / fabric entity types
    domain_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    fabric_entity_types_json: Mapped[str] = mapped_column(Text, default="[]")
    readiness: Mapped[str] = mapped_column(String(40), default="ready", index=True)  # ready|partial|planned
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("ecosystem_code", "code", name="uq_ecosystem_capability"),
        Index("ix_eco_cap_eco_ready", "ecosystem_code", "readiness"),
    )


class EcosystemEnrollment(Base):
    """Organization participation in an ecosystem role (tenant-scoped)."""

    __tablename__ = "ecosystem_enrollments"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    ecosystem_code: Mapped[str] = mapped_column(String(80), index=True)
    role_label: Mapped[str] = mapped_column(String(120), default="")  # e.g. Primary MRO, CAMO of record
    capabilities_enabled_json: Mapped[str] = mapped_column(Text, default="[]")
    isolation_mode: Mapped[str] = mapped_column(String(40), default="strict_tenant")
    data_ownership: Mapped[str] = mapped_column(String(40), default="organization")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "ecosystem_code", name="uq_eco_enrollment"),
        Index("ix_eco_enroll_org_status", "organization_id", "status"),
    )
