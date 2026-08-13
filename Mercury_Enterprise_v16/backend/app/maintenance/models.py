from __future__ import annotations

from datetime import datetime

from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..models import uid


class FaultCode(Base):
    """Organization-scoped fault / defect code catalog."""

    __tablename__ = "fault_codes"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300))
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_fault_code_org_code"),
        Index("ix_fault_codes_org_status", "organization_id", "status"),
    )


class CriticalTaskPolicy(Base):
    """Policy defining required certification steps for critical domains."""

    __tablename__ = "critical_task_policies"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    # engine | flight_controls | landing_gear | fuel | structural | propulsion | general
    domain: Mapped[str] = mapped_column(String(40), index=True)
    requires_inspector: Mapped[str] = mapped_column(String(10), default="true")
    requires_independent: Mapped[str] = mapped_column(String(10), default="false")
    requires_aca: Mapped[str] = mapped_column(String(10), default="true")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_critical_policy_org_code"),
        Index("ix_critical_task_policies_org_domain", "organization_id", "domain"),
    )


class MaintenanceTask(Base):
    """Organization-scoped maintenance task engine record (library + certification linked)."""

    __tablename__ = "maintenance_tasks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    task_number: Mapped[str] = mapped_column(String(80), index=True)
    # scheduled | unscheduled | corrective | preventive | inspection | functional_check |
    # operational_check | troubleshooting | component_replacement | deferred_defect |
    # mel_cdl | service_bulletin | engineering_order
    task_type: Mapped[str] = mapped_column(String(40), default="corrective", index=True)
    aircraft_id: Mapped[str] = mapped_column(String(80), index=True)
    fleet_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    registration: Mapped[str] = mapped_column(String(40), default="")
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(40), default="normal", index=True)  # low|normal|high|critical
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    estimated_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    actual_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    publication_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    publication_revision_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    component_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    serial_number: Mapped[str] = mapped_column(String(120), default="")
    required_parts: Mapped[str] = mapped_column(Text, default="")
    required_tools: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[str] = mapped_column(Text, default="")
    required_certification: Mapped[str] = mapped_column(String(200), default="")
    requires_inspector: Mapped[str] = mapped_column(String(10), default="true")
    independent_inspection_required: Mapped[str] = mapped_column(String(10), default="false")
    aca_required: Mapped[str] = mapped_column(String(10), default="false")
    fault_code_id: Mapped[str | None] = mapped_column(ForeignKey("fault_codes.id"), nullable=True, index=True)
    critical_policy_id: Mapped[str | None] = mapped_column(
        ForeignKey("critical_task_policies.id"), nullable=True, index=True
    )
    # open | assigned | started | in_progress | paused | completed |
    # awaiting_inspection | awaiting_aca | released | closed | rejected | cancelled
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    # not_released | released
    release_status: Mapped[str] = mapped_column(String(40), default="not_released", index=True)
    performed_by_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    assigned_to_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    certification_events: Mapped[list["CertificationEvent"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="CertificationEvent.occurred_at"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "task_number", name="uq_maintenance_task_org_number"),
        Index("ix_maintenance_tasks_org_status", "organization_id", "status"),
        Index("ix_maintenance_tasks_org_aircraft", "organization_id", "aircraft_id"),
        Index("ix_maintenance_tasks_org_type", "organization_id", "task_type"),
        Index("ix_maintenance_tasks_org_priority", "organization_id", "priority"),
        Index("ix_maintenance_tasks_org_fleet", "organization_id", "fleet_id"),
        Index("ix_maintenance_tasks_org_pub", "organization_id", "publication_id"),
    )


class DigitalSignature(Base):
    """Immutable digital signature record — never update."""

    __tablename__ = "digital_signatures"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    signer_employee_id: Mapped[str] = mapped_column(String(80), index=True)
    signer_username: Mapped[str] = mapped_column(String(120), default="")
    # password | pin | pki | smart_card | biometric_ready
    method: Mapped[str] = mapped_column(String(40), index=True)
    purpose: Mapped[str] = mapped_column(String(120), default="")
    target_type: Mapped[str] = mapped_column(String(80), index=True)
    target_id: Mapped[str] = mapped_column(String(80), index=True)
    signature_hash: Mapped[str] = mapped_column(String(64))
    pin_verified: Mapped[str] = mapped_column(String(10), default="false")
    password_confirmed: Mapped[str] = mapped_column(String(10), default="false")
    pki_ready: Mapped[str] = mapped_column(String(10), default="false")
    smart_card_ready: Mapped[str] = mapped_column(String(10), default="false")
    biometric_ready: Mapped[str] = mapped_column(String(10), default="false")
    signed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    details: Mapped[str] = mapped_column(Text, default="")

    __table_args__ = (
        Index("ix_digital_signatures_org_target", "organization_id", "target_type", "target_id"),
    )


class CertificationEvent(Base):
    """Append-only certification workflow event."""

    __tablename__ = "certification_events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("maintenance_tasks.id"), index=True)
    # performed | inspected | independent_inspection | aca_certified | aircraft_released
    step: Mapped[str] = mapped_column(String(40), index=True)
    actor_employee_id: Mapped[str] = mapped_column(String(80), index=True)
    actor_username: Mapped[str] = mapped_column(String(120), default="")
    signature_id: Mapped[str | None] = mapped_column(ForeignKey("digital_signatures.id"), nullable=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    task: Mapped[MaintenanceTask] = relationship(back_populates="certification_events")

    __table_args__ = (Index("ix_certification_events_task_step", "task_id", "step"),)


class TechnicalLogEntry(Base):
    """Immutable aircraft technical logbook entry."""

    __tablename__ = "technical_log_entries"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    aircraft_id: Mapped[str] = mapped_column(String(80), index=True)
    registration: Mapped[str] = mapped_column(String(40), default="")
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("maintenance_tasks.id"), nullable=True, index=True)
    publication_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    publication_revision_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    component_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    serial_number: Mapped[str] = mapped_column(String(120), default="")
    mechanic_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    inspector_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    independent_inspector_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    aca_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    release_signature_id: Mapped[str | None] = mapped_column(
        ForeignKey("digital_signatures.id"), nullable=True, index=True
    )
    summary: Mapped[str] = mapped_column(String(400), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    details: Mapped[str] = mapped_column(Text, default="")

    __table_args__ = (
        Index("ix_technical_log_entries_org_aircraft", "organization_id", "aircraft_id"),
        Index("ix_technical_log_entries_org_occurred", "organization_id", "occurred_at"),
    )


class AiDocumentIndexStub(Base):
    """AI-ready document index placeholder — no embeddings computed."""

    __tablename__ = "ai_document_index_stubs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    source_id: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending_index", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    embeddings: Mapped[list["AiEmbeddingStub"]] = relationship(
        back_populates="index_stub", cascade="all, delete-orphan"
    )


class AiEmbeddingStub(Base):
    """AI-ready embedding placeholder — no vectors stored."""

    __tablename__ = "ai_embedding_stubs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    index_id: Mapped[str] = mapped_column(ForeignKey("ai_document_index_stubs.id"), index=True)
    model_name: Mapped[str] = mapped_column(String(120), default="")
    dimensions: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="not_computed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    index_stub: Mapped[AiDocumentIndexStub] = relationship(back_populates="embeddings")


class AiKnowledgeCrossRef(Base):
    """Knowledge graph cross-reference between maintenance entities."""

    __tablename__ = "ai_knowledge_cross_refs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    from_type: Mapped[str] = mapped_column(String(80), index=True)
    from_id: Mapped[str] = mapped_column(String(80), index=True)
    to_type: Mapped[str] = mapped_column(String(80), index=True)
    to_id: Mapped[str] = mapped_column(String(80), index=True)
    # related_ata | related_component | related_task | related_fault
    relation: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ai_cross_refs_org_from", "organization_id", "from_type", "from_id"),
        Index("ix_ai_cross_refs_org_to", "organization_id", "to_type", "to_id"),
    )
