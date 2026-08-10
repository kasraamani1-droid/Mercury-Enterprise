import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def uid() -> str:
    return str(uuid.uuid4())

class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(40), default="open")
    severity: Mapped[str] = mapped_column(String(40), default="medium")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    organization_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    site_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    events: Mapped[list["TimelineEvent"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="incident", cascade="all, delete-orphan")

class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    incident: Mapped[Incident] = relationship(back_populates="events")

class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    provenance: Mapped[str] = mapped_column(String(40), default="operator_entered")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    organization_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    site_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    incident: Mapped[Incident] = relationship(back_populates="evidence")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(120))
    actor_role: Mapped[str] = mapped_column(String(40), default="")
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    site_id: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="api")
    outcome: Mapped[str] = mapped_column(String(40), default="success")
    origin: Mapped[str] = mapped_column(String(40), default="operator")
    details: Mapped[str] = mapped_column(Text, default="")
