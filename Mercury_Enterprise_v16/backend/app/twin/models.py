"""Program 15 — Mercury Digital Twin data model.

Lifecycle registry projecting over Universal Data Fabric passports.
History rows are append-only; passports never disappear.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


class TwinObject(Base):
    """Permanent Digital Twin for an aviation asset / entity."""

    __tablename__ = "twin_objects"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    twin_uuid: Mapped[str] = mapped_column(String(80), unique=True, index=True)  # permanent UUID
    twin_type: Mapped[str] = mapped_column(String(80), index=True)
    display_name: Mapped[str] = mapped_column(String(400))
    serial_number: Mapped[str] = mapped_column(String(120), default="", index=True)
    part_number: Mapped[str] = mapped_column(String(120), default="", index=True)
    passport_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    fabric_entity_type: Mapped[str] = mapped_column(String(80), default="")
    fabric_entity_id: Mapped[str] = mapped_column(String(80), default="")
    lifecycle_state: Mapped[str] = mapped_column(String(40), default="manufactured", index=True)
    ownership_json: Mapped[str] = mapped_column(Text, default="{}")
    current_configuration_id: Mapped[str] = mapped_column(String(80), default="")
    utilization_json: Mapped[str] = mapped_column(Text, default="{}")
    llp_json: Mapped[str] = mapped_column(Text, default="[]")
    compliance_json: Mapped[str] = mapped_column(Text, default="{}")  # SB/AD
    certificates_json: Mapped[str] = mapped_column(Text, default="[]")
    documents_json: Mapped[str] = mapped_column(Text, default="[]")
    publications_json: Mapped[str] = mapped_column(Text, default="[]")
    images_json: Mapped[str] = mapped_column(Text, default="[]")
    attachments_json: Mapped[str] = mapped_column(Text, default="[]")
    signatures_json: Mapped[str] = mapped_column(Text, default="[]")
    relationships_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    visualization_ready: Mapped[str] = mapped_column(String(10), default="false")  # future 3D
    weight_balance_ready: Mapped[str] = mapped_column(String(10), default="false")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    # Soft-delete never true for passports; twin may be archived but row retained
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "twin_type", "serial_number", "part_number", name="uq_twin_identity"),
        Index("ix_twin_org_type_state", "organization_id", "twin_type", "lifecycle_state"),
        Index("ix_twin_passport", "passport_id"),
    )


class TwinHistoryEntry(Base):
    """Immutable lifecycle / domain history entry (append-only)."""

    __tablename__ = "twin_history_entries"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    twin_id: Mapped[str] = mapped_column(String(80), index=True)
    history_kind: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    related_ref: Mapped[str] = mapped_column(String(200), default="")  # WO / finding / etc.
    fabric_event_id: Mapped[str] = mapped_column(String(80), default="")
    actor: Mapped[str] = mapped_column(String(120), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        Index("ix_twin_hist_twin_kind", "twin_id", "history_kind", "occurred_at"),
    )


class TwinConfiguration(Base):
    """Aircraft / asset configuration baseline (current / previous / planned)."""

    __tablename__ = "twin_configurations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    twin_id: Mapped[str] = mapped_column(String(80), index=True)
    baseline: Mapped[str] = mapped_column(String(40), index=True)  # current|previous|future_planned
    version_label: Mapped[str] = mapped_column(String(80), default="")
    configuration_json: Mapped[str] = mapped_column(Text, default="{}")
    engineering_changes_json: Mapped[str] = mapped_column(Text, default="[]")
    approved_modifications_json: Mapped[str] = mapped_column(Text, default="[]")
    optional_equipment_json: Mapped[str] = mapped_column(Text, default="[]")
    weight_balance_json: Mapped[str] = mapped_column(Text, default="{}")
    visualization_meta_json: Mapped[str] = mapped_column(Text, default="{}")  # future 3D hooks
    effective_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_twin_cfg_twin_baseline", "twin_id", "baseline"),)


class TwinReliabilitySnapshot(Base):
    """Architecture-only reliability metrics (no live analytics engine)."""

    __tablename__ = "twin_reliability_snapshots"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    twin_id: Mapped[str] = mapped_column(String(80), index=True)
    metric_code: Mapped[str] = mapped_column(String(80), index=True)
    metric_value: Mapped[str] = mapped_column(String(80), default="")
    unit: Mapped[str] = mapped_column(String(40), default="")
    window_label: Mapped[str] = mapped_column(String(80), default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    architecture_only: Mapped[str] = mapped_column(String(10), default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_twin_rel_twin_metric", "twin_id", "metric_code"),)


class TwinSearchEntry(Base):
    """Search projection for twin / serial / passport / configuration queries."""

    __tablename__ = "twin_search_entries"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    twin_id: Mapped[str] = mapped_column(String(80), index=True)
    twin_uuid: Mapped[str] = mapped_column(String(80), index=True)
    twin_type: Mapped[str] = mapped_column(String(80), index=True)
    passport_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    serial_number: Mapped[str] = mapped_column(String(120), default="", index=True)
    title: Mapped[str] = mapped_column(String(400))
    summary: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "twin_id", name="uq_twin_search"),
        Index("ix_twin_search_serial", "organization_id", "serial_number"),
    )
