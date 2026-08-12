from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AtaChapterCreate(BaseModel):
    chapter_number: str = Field(min_length=1, max_length=10)
    subchapter: str = Field(default="00", max_length=10)
    title: str = Field(min_length=2, max_length=200)
    description: str = ""


class AtaChapterOut(BaseModel):
    id: str
    chapter_number: str
    subchapter: str
    title: str
    description: str
    status: str


class CatalogItemCreate(BaseModel):
    part_number: str = Field(min_length=1, max_length=120)
    manufacturer_id: str | None = None
    oem_name: str = ""
    description: str = ""
    ata_chapter_id: str | None = None
    component_type: str = "general"
    is_serialized: bool = True
    is_life_limited: bool = False
    hour_limit: Decimal | None = None
    cycle_limit: int | None = Field(default=None, ge=0)
    calendar_limit_days: int | None = Field(default=None, ge=0)


class CatalogItemOut(BaseModel):
    id: str
    part_number: str
    manufacturer_id: str | None
    oem_name: str
    description: str
    ata_chapter_id: str | None
    component_type: str
    is_serialized: bool
    is_life_limited: bool
    hour_limit: Decimal | None
    cycle_limit: int | None
    calendar_limit_days: int | None
    status: str


class SerializedComponentCreate(BaseModel):
    catalog_item_id: str
    serial_number: str = Field(min_length=1, max_length=120)
    manufacturer_name: str = ""
    component_status: str = "stores"
    tsn_hours: Decimal = Decimal("0.00")
    csn_cycles: int = Field(default=0, ge=0)
    tso_hours: Decimal = Decimal("0.00")
    cso_cycles: int = Field(default=0, ge=0)
    hour_limit: Decimal | None = None
    cycle_limit: int | None = Field(default=None, ge=0)
    calendar_limit_days: int | None = Field(default=None, ge=0)
    due_date: datetime | None = None
    notes: str = ""
    organization_id: str | None = None


class SerializedComponentOut(BaseModel):
    id: str
    organization_id: str
    catalog_item_id: str
    part_number: str | None = None
    component_type: str | None = None
    serial_number: str
    manufacturer_name: str
    component_status: str
    current_aircraft_id: str | None
    installation_position: str | None
    date_installed: datetime | None
    date_removed: datetime | None
    tsn_hours: Decimal
    csn_cycles: int
    tso_hours: Decimal
    cso_cycles: int
    aircraft_hours_at_install: Decimal | None
    aircraft_cycles_at_install: int | None
    hour_limit: Decimal | None
    cycle_limit: int | None
    calendar_limit_days: int | None
    remaining_hours: Decimal | None
    remaining_cycles: int | None
    due_date: datetime | None
    notes: str
    status: str


class LifeLimitUpdate(BaseModel):
    hour_limit: Decimal | None = None
    cycle_limit: int | None = Field(default=None, ge=0)
    calendar_limit_days: int | None = Field(default=None, ge=0)
    due_date: datetime | None = None


class TimeCycleUpdate(BaseModel):
    tsn_hours: Decimal | None = None
    csn_cycles: int | None = Field(default=None, ge=0)
    tso_hours: Decimal | None = None
    cso_cycles: int | None = Field(default=None, ge=0)


class InstallRequest(BaseModel):
    aircraft_id: str
    position: str = Field(min_length=1, max_length=80)
    aircraft_hours: Decimal = Field(default=Decimal("0.00"), ge=0)
    aircraft_cycles: int = Field(default=0, ge=0)
    occurred_at: datetime | None = None
    reason: str = ""
    reference: str = ""


class RemoveRequest(BaseModel):
    destination_status: str = Field(default="stores", pattern="^(stores|maintenance|retired|quarantine)$")
    aircraft_hours: Decimal = Field(default=Decimal("0.00"), ge=0)
    aircraft_cycles: int = Field(default=0, ge=0)
    occurred_at: datetime | None = None
    reason: str = ""
    reference: str = ""


class TransferRequest(BaseModel):
    """Move between aircraft, stores, or maintenance. Installs if to_aircraft_id set."""

    to_status: str = Field(pattern="^(installed|stores|maintenance|retired|quarantine)$")
    to_aircraft_id: str | None = None
    position: str | None = Field(default=None, max_length=80)
    aircraft_hours: Decimal = Field(default=Decimal("0.00"), ge=0)
    aircraft_cycles: int = Field(default=0, ge=0)
    occurred_at: datetime | None = None
    reason: str = ""
    reference: str = ""


class HistoryOut(BaseModel):
    id: str
    organization_id: str
    component_id: str
    event_type: str
    aircraft_id: str | None
    from_aircraft_id: str | None
    to_aircraft_id: str | None
    position: str | None
    from_status: str
    to_status: str
    occurred_at: datetime
    aircraft_hours: Decimal | None
    aircraft_cycles: int | None
    actor: str
    reason: str
    reference: str
    details: str


class AircraftConfigurationItem(BaseModel):
    component_id: str
    serial_number: str
    part_number: str
    component_type: str
    position: str
    date_installed: datetime | None
    tsn_hours: Decimal
    csn_cycles: int
    remaining_hours: Decimal | None
    remaining_cycles: int | None


class AircraftConfigurationOut(BaseModel):
    aircraft_id: str
    organization_id: str
    installed: list[AircraftConfigurationItem]
