from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..models import uid


class AtaChapter(Base):
    """Shared ATA chapter / subchapter catalog."""

    __tablename__ = "ata_chapters"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    chapter_number: Mapped[str] = mapped_column(String(10), index=True)
    subchapter: Mapped[str] = mapped_column(String(10), default="00", index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    catalog_items: Mapped[list["ComponentCatalogItem"]] = relationship(back_populates="ata_chapter")

    __table_args__ = (
        UniqueConstraint("chapter_number", "subchapter", name="uq_ata_chapter_sub"),
    )


class ComponentCatalogItem(Base):
    """Shared part-number catalog (OEM reference data)."""

    __tablename__ = "component_catalog"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    part_number: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    manufacturer_id: Mapped[str | None] = mapped_column(ForeignKey("manufacturers.id"), nullable=True, index=True)
    oem_name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(String(400), default="")
    ata_chapter_id: Mapped[str | None] = mapped_column(ForeignKey("ata_chapters.id"), nullable=True, index=True)
    component_type: Mapped[str] = mapped_column(String(40), default="general", index=True)
    is_serialized: Mapped[str] = mapped_column(String(10), default="true", index=True)
    is_life_limited: Mapped[str] = mapped_column(String(10), default="false", index=True)
    hour_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cycle_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calendar_limit_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ata_chapter: Mapped[AtaChapter | None] = relationship(back_populates="catalog_items")
    components: Mapped[list["SerializedComponent"]] = relationship(back_populates="catalog_item")


class SerializedComponent(Base):
    """Organization-owned serialized component instance."""

    __tablename__ = "serialized_components"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    catalog_item_id: Mapped[str] = mapped_column(ForeignKey("component_catalog.id"), index=True)
    serial_number: Mapped[str] = mapped_column(String(120), index=True)
    manufacturer_name: Mapped[str] = mapped_column(String(200), default="")
    # installed | stores | maintenance | retired | quarantine
    component_status: Mapped[str] = mapped_column(String(40), default="stores", index=True)
    current_aircraft_id: Mapped[str | None] = mapped_column(ForeignKey("aircraft.id"), nullable=True, index=True)
    installation_position: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    date_installed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    date_removed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tsn_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    csn_cycles: Mapped[int] = mapped_column(Integer, default=0)
    tso_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    cso_cycles: Mapped[int] = mapped_column(Integer, default=0)

    aircraft_hours_at_install: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    aircraft_cycles_at_install: Mapped[int | None] = mapped_column(Integer, nullable=True)

    hour_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cycle_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calendar_limit_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remaining_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    remaining_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    catalog_item: Mapped[ComponentCatalogItem] = relationship(back_populates="components")
    history: Mapped[list["ComponentInstallationHistory"]] = relationship(
        back_populates="component",
        cascade="all, delete-orphan",
        order_by="ComponentInstallationHistory.occurred_at.desc()",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "serial_number", name="uq_component_org_serial"),
        Index("ix_serialized_components_org_status", "organization_id", "component_status"),
        Index("ix_serialized_components_org_aircraft", "organization_id", "current_aircraft_id"),
        Index("ix_serialized_components_org_catalog", "organization_id", "catalog_item_id"),
        # At most one installed occupant of a given position on an aircraft.
        UniqueConstraint(
            "current_aircraft_id",
            "installation_position",
            name="uq_aircraft_position_occupant",
        ),
    )


class ComponentInstallationHistory(Base):
    """Immutable install / remove / transfer history."""

    __tablename__ = "component_installation_history"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    component_id: Mapped[str] = mapped_column(ForeignKey("serialized_components.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)  # install | remove | transfer
    aircraft_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    from_aircraft_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    to_aircraft_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    position: Mapped[str | None] = mapped_column(String(80), nullable=True)
    from_status: Mapped[str] = mapped_column(String(40), default="")
    to_status: Mapped[str] = mapped_column(String(40), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    aircraft_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    aircraft_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor: Mapped[str] = mapped_column(String(120), default="")
    reason: Mapped[str] = mapped_column(String(400), default="")
    reference: Mapped[str] = mapped_column(String(120), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    component: Mapped[SerializedComponent] = relationship(back_populates="history")

    __table_args__ = (
        Index("ix_comp_hist_org_component", "organization_id", "component_id"),
        Index("ix_comp_hist_org_aircraft", "organization_id", "aircraft_id"),
        Index("ix_comp_hist_org_event", "organization_id", "event_type"),
    )
