"""Program 16 — Mercury Plugin Platform models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


class PluginDefinition(Base):
    """Global plugin catalog entry."""

    __tablename__ = "plugin_definitions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80), index=True)
    connect_connector: Mapped[str] = mapped_column(String(80), index=True, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    readiness: Mapped[str] = mapped_column(String(40), default="planned", index=True)
    # Architecture disclaimer for OEM / safety plugins
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default="Plugin architecture readiness only. Live vendor adapters are future Connect bindings.",
    )
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PluginInstallation(Base):
    """Org-scoped plugin installation / enablement (no secrets)."""

    __tablename__ = "plugin_installations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    plugin_code: Mapped[str] = mapped_column(String(80), index=True)
    install_status: Mapped[str] = mapped_column(String(40), default="installed", index=True)
    connect_binding_id: Mapped[str] = mapped_column(String(80), default="")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    config_ref: Mapped[str] = mapped_column(String(200), default="")  # vault ref only
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "plugin_code", name="uq_plugin_install"),
        Index("ix_plugin_install_org_status", "organization_id", "install_status"),
    )


class PluginDashboardLayout(Base):
    """Custom dashboard layout architecture (tenant-scoped widgets JSON)."""

    __tablename__ = "plugin_dashboard_layouts"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    widgets_json: Mapped[str] = mapped_column(Text, default="[]")
    is_default: Mapped[str] = mapped_column(String(10), default="false")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_plugin_dash_org", "organization_id", "status"),)
