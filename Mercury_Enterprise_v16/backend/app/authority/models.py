"""Authority portal readiness — civil aviation authorities (no regulatory claim)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


class AuthorityBody(Base):
    """Registry of authorities for future oversight / digital approval portals.

    Mercury does NOT claim regulatory approval or certification authority.
    """

    __tablename__ = "authority_bodies"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(80), default="")
    portal_status: Mapped[str] = mapped_column(String(40), default="ready", index=True)
    capabilities_json: Mapped[str] = mapped_column(
        Text, default='["audit","oversight","compliance","digital_certificates","digital_approvals"]'
    )
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default="Not certified operational software. No regulatory approval claimed.",
    )
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
