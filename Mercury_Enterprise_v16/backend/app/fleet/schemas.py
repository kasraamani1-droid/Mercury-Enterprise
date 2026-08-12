from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ManufacturerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40)
    country: str = ""


class ManufacturerOut(BaseModel):
    id: str
    name: str
    code: str
    country: str
    status: str


class AircraftModelCreate(BaseModel):
    manufacturer_id: str
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40)
    icao_type: str = ""
    category: str = "fixed_wing"
    engine_count: int = Field(default=2, ge=0, le=12)
    max_seats: int | None = Field(default=None, ge=0, le=1000)


class AircraftModelOut(BaseModel):
    id: str
    manufacturer_id: str
    name: str
    code: str
    icao_type: str
    category: str
    engine_count: int
    max_seats: int | None
    status: str


class AircraftStatusOut(BaseModel):
    code: str
    name: str
    description: str
    is_operational: bool
    sort_order: int
    status: str


class FleetOperatorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40)
    icao_code: str = ""
    iata_code: str = ""
    country: str = ""
    organization_id: str | None = None


class FleetOperatorOut(BaseModel):
    id: str
    organization_id: str
    name: str
    code: str
    icao_code: str
    iata_code: str
    country: str
    status: str


class FleetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40)
    operator_id: str | None = None
    base_site_id: str | None = None
    notes: str = ""
    organization_id: str | None = None


class FleetOut(BaseModel):
    id: str
    organization_id: str
    operator_id: str | None
    name: str
    code: str
    base_site_id: str | None
    status: str
    notes: str
    aircraft_count: int = 0


class AircraftCreate(BaseModel):
    model_id: str
    serial_number: str = Field(min_length=1, max_length=120)
    manufacturer_serial: str = ""
    year_built: int | None = Field(default=None, ge=1900, le=2100)
    fleet_id: str | None = None
    operator_id: str | None = None
    status_code: str = "active"
    home_base_site_id: str | None = None
    registration_mark: str | None = Field(default=None, max_length=40)
    registration_country: str = ""
    notes: str = ""
    organization_id: str | None = None


class AircraftOut(BaseModel):
    id: str
    organization_id: str
    model_id: str
    fleet_id: str | None
    operator_id: str | None
    status_code: str
    serial_number: str
    manufacturer_serial: str
    year_built: int | None
    home_base_site_id: str | None
    notes: str
    status: str
    current_registration: str | None = None


class AircraftStatusUpdate(BaseModel):
    status_code: str = Field(min_length=2, max_length=40)


class RegistrationCreate(BaseModel):
    aircraft_id: str
    registration_mark: str = Field(min_length=2, max_length=40)
    country: str = ""
    make_current: bool = True
    notes: str = ""
    organization_id: str | None = None


class RegistrationOut(BaseModel):
    id: str
    organization_id: str
    aircraft_id: str
    registration_mark: str
    country: str
    is_current: bool
    effective_from: datetime | None
    effective_to: datetime | None
    status: str
    notes: str
