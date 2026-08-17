"""Mercury Connect connector registry models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


class ConnectConnector(Base):
    """Global connector type in Mercury Connect (ERP, IdP, OEM, courier, …)."""

    __tablename__ = "connect_connectors"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80), index=True)
    # erp|accounting|identity|oem|payment|courier|email|sms|storage|weather|flight_ops|efb|other
    description: Mapped[str] = mapped_column(Text, default="")
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    auth_modes_json: Mapped[str] = mapped_column(Text, default='["api_key","oauth2","mtls"]')
    direction: Mapped[str] = mapped_column(String(40), default="bidirectional")  # in|out|bidirectional
    readiness: Mapped[str] = mapped_column(String(40), default="ready", index=True)
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ConnectBinding(Base):
    """Org-scoped connector binding metadata (no secrets stored here)."""

    __tablename__ = "connect_bindings"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    # configured|testing|live|disabled
    binding_status: Mapped[str] = mapped_column(String(40), default="configured", index=True)
    config_ref: Mapped[str] = mapped_column(String(200), default="")  # vault/secret ref only
    endpoint_hint: Mapped[str] = mapped_column(String(400), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "connector_code", "display_name", name="uq_connect_binding"),
        Index("ix_connect_bind_org_status", "organization_id", "binding_status"),
    )
