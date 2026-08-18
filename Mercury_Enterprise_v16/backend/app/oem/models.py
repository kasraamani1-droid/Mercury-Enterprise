"""OEM / manufacturer portal readiness — manufacturer master registry."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


class OemManufacturer(Base):
    """Canonical manufacturer record for future OEM portals.

    Owns future: products, publications, SBs, training, marketplace, support.
    """

    __tablename__ = "oem_manufacturers"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(40), default="airframe")  # airframe|engine|avionics|systems
    country_code: Mapped[str] = mapped_column(String(8), default="")
    portal_status: Mapped[str] = mapped_column(String(40), default="ready", index=True)
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
