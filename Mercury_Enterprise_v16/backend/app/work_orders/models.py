from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..models import uid


class WorkPackage(Base):
    """Planning container for one aircraft visit / check."""

    __tablename__ = "work_packages"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    package_number: Mapped[str] = mapped_column(String(80), index=True)
    fleet_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    aircraft_id: Mapped[str] = mapped_column(String(80), index=True)
    registration: Mapped[str] = mapped_column(String(40), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    # draft | planned | in_progress | completed | released | closed | cancelled
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="normal", index=True)
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_finish: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_finish: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planner_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    supervisor_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    hangar_bay: Mapped[str] = mapped_column(String(80), default="")
    shift_code: Mapped[str] = mapped_column(String(40), default="")
    estimated_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    actual_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    work_orders: Mapped[list["WorkOrder"]] = relationship(
        back_populates="work_package", cascade="all, delete-orphan", order_by="WorkOrder.created_at"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "package_number", name="uq_work_package_org_number"),
        Index("ix_work_packages_org_status", "organization_id", "status"),
        Index("ix_work_packages_org_aircraft", "organization_id", "aircraft_id"),
    )


class WorkOrder(Base):
    """Work order under a package — groups job cards by ATA/scope."""

    __tablename__ = "work_orders"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    work_package_id: Mapped[str] = mapped_column(ForeignKey("work_packages.id"), index=True)
    wo_number: Mapped[str] = mapped_column(String(80), index=True)
    aircraft_id: Mapped[str] = mapped_column(String(80), index=True)
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    # draft | open | in_progress | delayed | completed | released | closed | cancelled
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="normal", index=True)
    planner_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    supervisor_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    publication_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    publication_revision_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    estimated_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    actual_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    work_package: Mapped[WorkPackage] = relationship(back_populates="work_orders")
    job_cards: Mapped[list["JobCard"]] = relationship(
        back_populates="work_order", cascade="all, delete-orphan", order_by="JobCard.created_at"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "wo_number", name="uq_work_order_org_number"),
        Index("ix_work_orders_org_status", "organization_id", "status"),
        Index("ix_work_orders_package", "work_package_id"),
    )


class JobCard(Base):
    """Executable maintenance job card — links to MaintenanceTask for certify/logbook."""

    __tablename__ = "job_cards"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    work_order_id: Mapped[str] = mapped_column(ForeignKey("work_orders.id"), index=True)
    job_card_number: Mapped[str] = mapped_column(String(80), index=True)
    maintenance_task_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    aircraft_id: Mapped[str] = mapped_column(String(80), index=True)
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    # draft | assigned | accepted | in_progress | paused | waiting_parts |
    # waiting_engineering | waiting_inspection | completed | rejected | released | closed
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="normal", index=True)
    publication_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    publication_revision_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    component_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    required_parts: Mapped[str] = mapped_column(Text, default="")
    required_tools: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[str] = mapped_column(Text, default="")
    required_certification: Mapped[str] = mapped_column(String(200), default="")
    estimated_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    actual_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    technician_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    inspector_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    independent_inspector_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    aca_employee_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    hangar_bay: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    rework_reason: Mapped[str] = mapped_column(Text, default="")
    independent_inspection_required: Mapped[str] = mapped_column(String(10), default="false")
    aca_required: Mapped[str] = mapped_column(String(10), default="true")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    work_order: Mapped[WorkOrder] = relationship(back_populates="job_cards")
    attachments: Mapped[list["JobCardAttachment"]] = relationship(
        back_populates="job_card", cascade="all, delete-orphan", order_by="JobCardAttachment.created_at"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "job_card_number", name="uq_job_card_org_number"),
        Index("ix_job_cards_org_status", "organization_id", "status"),
        Index("ix_job_cards_technician", "organization_id", "technician_employee_id"),
        Index("ix_job_cards_work_order", "work_order_id"),
    )


class JobCardAttachment(Base):
    """Photo / note / document attachment metadata (locator only — no OEM binary storage)."""

    __tablename__ = "job_card_attachments"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    job_card_id: Mapped[str] = mapped_column(ForeignKey("job_cards.id"), index=True)
    # photo | note | document | drawing
    kind: Mapped[str] = mapped_column(String(40), default="note", index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    storage_uri: Mapped[str] = mapped_column(String(500), default="")
    content_type: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job_card: Mapped[JobCard] = relationship(back_populates="attachments")

    __table_args__ = (Index("ix_job_card_attachments_card", "job_card_id"),)
