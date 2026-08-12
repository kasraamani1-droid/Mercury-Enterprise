from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..models import uid


class Manufacturer(Base):
    """Shared aviation manufacturer catalog (not tenant-scoped)."""

    __tablename__ = "manufacturers"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    country: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    models: Mapped[list["AircraftModel"]] = relationship(back_populates="manufacturer", cascade="all, delete-orphan")


class AircraftModel(Base):
    """Shared aircraft type/model catalog."""

    __tablename__ = "aircraft_models"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    manufacturer_id: Mapped[str] = mapped_column(ForeignKey("manufacturers.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    icao_type: Mapped[str] = mapped_column(String(20), default="", index=True)
    category: Mapped[str] = mapped_column(String(40), default="fixed_wing")
    engine_count: Mapped[int] = mapped_column(Integer, default=2)
    max_seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    manufacturer: Mapped[Manufacturer] = relationship(back_populates="models")
    aircraft: Mapped[list["Aircraft"]] = relationship(back_populates="model")

    __table_args__ = (UniqueConstraint("manufacturer_id", "code", name="uq_aircraft_model_mfr_code"),)


class AircraftStatus(Base):
    """Canonical aircraft operational status codes."""

    __tablename__ = "aircraft_statuses"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_operational: Mapped[str] = mapped_column(String(10), default="false", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FleetOperator(Base):
    """Aviation operator (airline / AOC holder) scoped to a Mercury organization."""

    __tablename__ = "fleet_operators"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(40))
    icao_code: Mapped[str] = mapped_column(String(10), default="", index=True)
    iata_code: Mapped[str] = mapped_column(String(10), default="")
    country: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fleets: Mapped[list["Fleet"]] = relationship(back_populates="operator")
    aircraft: Mapped[list["Aircraft"]] = relationship(back_populates="operator")

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_fleet_operator_org_code"),
        Index("ix_fleet_operators_org_status", "organization_id", "status"),
    )


class Fleet(Base):
    """Named fleet grouping within an organization."""

    __tablename__ = "fleets"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    operator_id: Mapped[str | None] = mapped_column(ForeignKey("fleet_operators.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(40))
    base_site_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    operator: Mapped[FleetOperator | None] = relationship(back_populates="fleets")
    aircraft: Mapped[list["Aircraft"]] = relationship(back_populates="fleet")

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_fleet_org_code"),
        Index("ix_fleets_org_status", "organization_id", "status"),
    )


class Aircraft(Base):
    """Physical airframe tracked by an organization."""

    __tablename__ = "aircraft"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("aircraft_models.id"), index=True)
    fleet_id: Mapped[str | None] = mapped_column(ForeignKey("fleets.id"), nullable=True, index=True)
    operator_id: Mapped[str | None] = mapped_column(ForeignKey("fleet_operators.id"), nullable=True, index=True)
    status_code: Mapped[str] = mapped_column(ForeignKey("aircraft_statuses.code"), default="active", index=True)
    serial_number: Mapped[str] = mapped_column(String(120), index=True)
    manufacturer_serial: Mapped[str] = mapped_column(String(120), default="")
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_base_site_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    model: Mapped[AircraftModel] = relationship(back_populates="aircraft")
    fleet: Mapped[Fleet | None] = relationship(back_populates="aircraft")
    operator: Mapped[FleetOperator | None] = relationship(back_populates="aircraft")
    registrations: Mapped[list["Registration"]] = relationship(back_populates="aircraft", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("organization_id", "serial_number", name="uq_aircraft_org_serial"),
        Index("ix_aircraft_org_status", "organization_id", "status"),
        Index("ix_aircraft_org_status_code", "organization_id", "status_code"),
    )


class Registration(Base):
    """Civil registration mark history for an aircraft."""

    __tablename__ = "registrations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    aircraft_id: Mapped[str] = mapped_column(ForeignKey("aircraft.id"), index=True)
    registration_mark: Mapped[str] = mapped_column(String(40), index=True)
    country: Mapped[str] = mapped_column(String(80), default="")
    is_current: Mapped[str] = mapped_column(String(10), default="true", index=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    aircraft: Mapped[Aircraft] = relationship(back_populates="registrations")

    __table_args__ = (
        UniqueConstraint("registration_mark", name="uq_registration_mark"),
        Index("ix_registrations_org_aircraft", "organization_id", "aircraft_id"),
        Index("ix_registrations_org_current", "organization_id", "is_current"),
    )
