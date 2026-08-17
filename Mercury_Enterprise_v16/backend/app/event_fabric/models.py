"""Program 17 — Enterprise Event Fabric persistence.

Durable, immutable enterprise event store — distinct from fabric_events
(Digital Thread timeline) and in-memory Event Framework history.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


class EnterpriseEventType(Base):
    """Versioned event catalog entry."""

    __tablename__ = "enterprise_event_types"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(120), index=True)
    family: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    description: Mapped[str] = mapped_column(Text, default="")
    severity_default: Mapped[str] = mapped_column(String(40), default="info")
    schema_json: Mapped[str] = mapped_column(Text, default="{}")
    ai_ready: Mapped[str] = mapped_column(String(10), default="true")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_enterprise_event_type_ver"),
        Index("ix_enterprise_event_type_family", "family", "status"),
    )


class EnterpriseEventStore(Base):
    """Immutable enterprise event log (append-only)."""

    __tablename__ = "enterprise_event_store"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    event_code: Mapped[str] = mapped_column(String(120), index=True)
    event_version: Mapped[str] = mapped_column(String(20), default="1.0")
    family: Mapped[str] = mapped_column(String(80), index=True, default="")
    bus_event_type: Mapped[str] = mapped_column(String(200), default="")  # dotted runtime name
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    actor: Mapped[str] = mapped_column(String(120), default="")
    source_service: Mapped[str] = mapped_column(String(120), default="")
    target_service: Mapped[str] = mapped_column(String(120), default="")
    correlation_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    trace_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    severity: Mapped[str] = mapped_column(String(40), default="info", index=True)
    status: Mapped[str] = mapped_column(String(40), default="published", index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    # No updated_at / deleted_at — immutable

    __table_args__ = (
        Index("ix_enterprise_store_org_code", "organization_id", "event_code", "occurred_at"),
        Index("ix_enterprise_store_org_family", "organization_id", "family"),
    )


class EnterpriseEventSubscription(Base):
    """Persisted subscription registry (handler endpoint metadata)."""

    __tablename__ = "enterprise_event_subscriptions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True, default="")  # empty = global
    event_code: Mapped[str] = mapped_column(String(120), index=True)  # or *
    subscriber_name: Mapped[str] = mapped_column(String(200))
    filter_json: Mapped[str] = mapped_column(Text, default="{}")
    endpoint_hint: Mapped[str] = mapped_column(String(400), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "event_code", "subscriber_name", name="uq_enterprise_sub"
        ),
    )


class EnterpriseEventDeadLetter(Base):
    """Dead letter queue for failed deliveries / handler errors."""

    __tablename__ = "enterprise_event_dlq"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    store_event_id: Mapped[str] = mapped_column(String(80), index=True)
    event_code: Mapped[str] = mapped_column(String(120), index=True)
    subscriber_name: Mapped[str] = mapped_column(String(200), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)  # open|retried|resolved
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_enterprise_dlq_org_status", "organization_id", "status"),)


class EnterpriseEventReplay(Base):
    """Replay job metadata for event store reprocessing."""

    __tablename__ = "enterprise_event_replays"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    event_code: Mapped[str] = mapped_column(String(120), default="")
    from_occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    to_occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    events_replayed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="completed", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
