from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..org.service import OrganizationService
from .models import (
    Aircraft,
    AircraftFamily,
    AircraftModel,
    AircraftStatus,
    Fleet,
    FleetOperator,
    Manufacturer,
    Registration,
)
from .repository import FleetRepository
from .schemas import (
    AircraftCreate,
    AircraftFamilyOut,
    AircraftModelCreate,
    AircraftModelOut,
    AircraftOut,
    AircraftStatusOut,
    FleetCreate,
    FleetOperatorCreate,
    FleetOperatorOut,
    FleetOut,
    ManufacturerCreate,
    ManufacturerOut,
    RegistrationCreate,
    RegistrationOut,
)

logger = logging.getLogger("mercury.fleet")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _truthy(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


class FleetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = FleetRepository(db)
        self.org = OrganizationService(db)

    def ensure_seed_data(self) -> None:
        """Idempotent catalog + demo fleet for org-aviation-east."""
        pending = False
        if not self.repo.list_statuses(active_only=False):
            for code, name, operational, order, description in (
                ("active", "Active", True, 10, "Serviceable and available"),
                ("maintenance", "Maintenance", False, 20, "Scheduled or unscheduled maintenance"),
                ("grounded", "Grounded", False, 30, "Temporarily grounded"),
                ("reserved", "Reserved", False, 40, "Reserved / not in active rotation"),
                ("retired", "Retired", False, 50, "Permanently withdrawn"),
            ):
                self.repo.add_status(
                    AircraftStatus(
                        code=code,
                        name=name,
                        description=description,
                        is_operational="true" if operational else "false",
                        sort_order=order,
                        status="active",
                        created_at=_utcnow(),
                        updated_at=_utcnow(),
                    )
                )
            pending = True

        if not self.repo.list_manufacturers(active_only=False):
            airbus = Manufacturer(
                id="mfr-airbus",
                name="Airbus",
                code="AIRBUS",
                country="FR",
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            boeing = Manufacturer(
                id="mfr-boeing",
                name="Boeing",
                code="BOEING",
                country="US",
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            self.repo.add_manufacturer(airbus)
            self.repo.add_manufacturer(boeing)
            self.repo.add_family(
                AircraftFamily(
                    id="family-a320",
                    manufacturer_id=airbus.id,
                    name="A320 Family",
                    code="A320F",
                    description="A320ceo/neo family",
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
            )
            self.repo.add_model(
                AircraftModel(
                    id="model-a320",
                    manufacturer_id=airbus.id,
                    family_id="family-a320",
                    name="A320-200",
                    code="A320",
                    icao_type="A320",
                    category="fixed_wing",
                    engine_count=2,
                    max_seats=180,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
            )
            self.repo.add_model(
                AircraftModel(
                    id="model-b737",
                    manufacturer_id=boeing.id,
                    name="737-800",
                    code="B738",
                    icao_type="B738",
                    category="fixed_wing",
                    engine_count=2,
                    max_seats=189,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
            )
            pending = True

        if pending:
            self.repo.commit()

        # Backfill aircraft family for long-lived DBs created before Sprint 7b.
        if self.repo.get_family("family-a320") is None and self.repo.get_manufacturer("mfr-airbus") is not None:
            self.repo.add_family(
                AircraftFamily(
                    id="family-a320",
                    manufacturer_id="mfr-airbus",
                    name="A320 Family",
                    code="A320F",
                    description="A320ceo/neo family",
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
            )
            model = self.repo.get_model("model-a320")
            if model is not None and not model.family_id:
                model.family_id = "family-a320"
                model.updated_at = _utcnow()
            self.repo.commit()

        # Tenant demo data (requires organizations seed).
        org_id = "org-aviation-east"
        if self.org.repo.get_organization(org_id) is None:
            return
        if self.repo.list_operators(organization_id=org_id, active_only=False):
            return

        operator = FleetOperator(
            id="op-mercury-east",
            organization_id=org_id,
            name="Mercury East Airlines",
            code="MEA",
            icao_code="MEA",
            iata_code="ME",
            country="CA",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_operator(operator)
        fleet = Fleet(
            id="fleet-east-narrow",
            organization_id=org_id,
            operator_id=operator.id,
            name="East Narrowbody",
            code="EAST-NB",
            base_site_id="site-cyul",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_fleet(fleet)
        self.repo.flush()

        ac1 = Aircraft(
            id="ac-c-gmea",
            organization_id=org_id,
            model_id="model-a320",
            fleet_id=fleet.id,
            operator_id=operator.id,
            status_code="active",
            serial_number="A320-1001",
            manufacturer_serial="MSN-1001",
            year_built=2018,
            home_base_site_id="site-cyul",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        ac2 = Aircraft(
            id="ac-c-gmeb",
            organization_id=org_id,
            model_id="model-b737",
            fleet_id=fleet.id,
            operator_id=operator.id,
            status_code="maintenance",
            serial_number="B738-2002",
            manufacturer_serial="LN-2002",
            year_built=2016,
            home_base_site_id="site-cyyz",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_aircraft(ac1)
        self.repo.add_aircraft(ac2)
        self.repo.flush()
        self.repo.add_registration(
            Registration(
                organization_id=org_id,
                aircraft_id=ac1.id,
                registration_mark="C-GMEA",
                country="CA",
                is_current="true",
                effective_from=_utcnow(),
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
        )
        self.repo.add_registration(
            Registration(
                organization_id=org_id,
                aircraft_id=ac2.id,
                registration_mark="C-GMEB",
                country="CA",
                is_current="true",
                effective_from=_utcnow(),
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
        )
        self.repo.commit()

    def _commit_or_conflict(self, *, detail: str) -> None:
        try:
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail=detail) from exc

    def assert_org_access(self, *, username: str, session_role: str, organization_id: str) -> None:
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=organization_id)

    def resolve_org_id(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        requested_org_id: str | None,
    ) -> str:
        org_id = (requested_org_id or session_org_id).strip()
        self.assert_org_access(username=username, session_role=session_role, organization_id=org_id)
        return org_id

    # --- serializers ---
    @staticmethod
    def manufacturer_out(row: Manufacturer) -> ManufacturerOut:
        return ManufacturerOut(
            id=row.id, name=row.name, code=row.code, country=row.country, status=row.status
        )

    @staticmethod
    def family_out(row: AircraftFamily) -> AircraftFamilyOut:
        return AircraftFamilyOut(
            id=row.id,
            manufacturer_id=row.manufacturer_id,
            name=row.name,
            code=row.code,
            description=row.description or "",
            status=row.status,
        )

    @staticmethod
    def model_out(row: AircraftModel) -> AircraftModelOut:
        return AircraftModelOut(
            id=row.id,
            manufacturer_id=row.manufacturer_id,
            family_id=getattr(row, "family_id", None),
            name=row.name,
            code=row.code,
            icao_type=row.icao_type,
            category=row.category,
            engine_count=row.engine_count,
            max_seats=row.max_seats,
            status=row.status,
        )

    @staticmethod
    def status_out(row: AircraftStatus) -> AircraftStatusOut:
        return AircraftStatusOut(
            code=row.code,
            name=row.name,
            description=row.description,
            is_operational=_truthy(row.is_operational),
            sort_order=row.sort_order,
            status=row.status,
        )

    @staticmethod
    def operator_out(row: FleetOperator) -> FleetOperatorOut:
        return FleetOperatorOut(
            id=row.id,
            organization_id=row.organization_id,
            name=row.name,
            code=row.code,
            icao_code=row.icao_code,
            iata_code=row.iata_code,
            country=row.country,
            status=row.status,
        )

    def fleet_out(self, row: Fleet, *, aircraft_count: int | None = None) -> FleetOut:
        count = self.repo.count_aircraft_in_fleet(row.id) if aircraft_count is None else aircraft_count
        return FleetOut(
            id=row.id,
            organization_id=row.organization_id,
            operator_id=row.operator_id,
            name=row.name,
            code=row.code,
            base_site_id=row.base_site_id,
            status=row.status,
            notes=row.notes,
            aircraft_count=count,
        )

    def list_fleets_for_org(self, organization_id: str) -> list[FleetOut]:
        rows = self.repo.list_fleets(organization_id=organization_id)
        counts = self.repo.count_aircraft_by_fleet(organization_id=organization_id)
        return [self.fleet_out(r, aircraft_count=counts.get(r.id, 0)) for r in rows]

    def aircraft_out(self, row: Aircraft, current_mark: str | None = None) -> AircraftOut:
        if current_mark is None:
            current = self.repo.get_current_registration(row.id)
            current_mark = current.registration_mark if current else None
        return AircraftOut(
            id=row.id,
            organization_id=row.organization_id,
            model_id=row.model_id,
            fleet_id=row.fleet_id,
            operator_id=row.operator_id,
            status_code=row.status_code,
            serial_number=row.serial_number,
            manufacturer_serial=row.manufacturer_serial,
            year_built=row.year_built,
            home_base_site_id=row.home_base_site_id,
            notes=row.notes,
            status=row.status,
            current_registration=current_mark,
        )

    @staticmethod
    def registration_out(row: Registration) -> RegistrationOut:
        return RegistrationOut(
            id=row.id,
            organization_id=row.organization_id,
            aircraft_id=row.aircraft_id,
            registration_mark=row.registration_mark,
            country=row.country,
            is_current=_truthy(row.is_current),
            effective_from=row.effective_from,
            effective_to=row.effective_to,
            status=row.status,
            notes=row.notes,
        )

    # --- catalog mutations ---
    def create_manufacturer(self, payload: ManufacturerCreate) -> ManufacturerOut:
        code = payload.code.strip().upper()
        if self.repo.get_manufacturer_by_code(code):
            raise HTTPException(status_code=409, detail="Manufacturer code already exists")
        row = Manufacturer(
            name=payload.name.strip(),
            code=code,
            country=(payload.country or "").strip().upper(),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_manufacturer(row)
        self._commit_or_conflict(detail="Manufacturer already exists")
        self.repo.refresh(row)
        return self.manufacturer_out(row)

    def create_model(self, payload: AircraftModelCreate) -> AircraftModelOut:
        if self.repo.get_manufacturer(payload.manufacturer_id) is None:
            raise HTTPException(status_code=404, detail="Manufacturer not found")
        row = AircraftModel(
            manufacturer_id=payload.manufacturer_id,
            name=payload.name.strip(),
            code=payload.code.strip().upper(),
            icao_type=(payload.icao_type or "").strip().upper(),
            category=(payload.category or "fixed_wing").strip(),
            engine_count=payload.engine_count,
            max_seats=payload.max_seats,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_model(row)
        self._commit_or_conflict(detail="Aircraft model code already exists for manufacturer")
        self.repo.refresh(row)
        return self.model_out(row)

    # --- tenant mutations ---
    def create_operator(
        self,
        payload: FleetOperatorCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> FleetOperatorOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        row = FleetOperator(
            organization_id=org_id,
            name=payload.name.strip(),
            code=payload.code.strip().upper(),
            icao_code=(payload.icao_code or "").strip().upper(),
            iata_code=(payload.iata_code or "").strip().upper(),
            country=(payload.country or "").strip().upper(),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_operator(row)
        self._commit_or_conflict(detail="Operator code already exists in organization")
        self.repo.refresh(row)
        return self.operator_out(row)

    def create_fleet(
        self,
        payload: FleetCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> FleetOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        if payload.operator_id:
            op = self.repo.get_operator(payload.operator_id)
            if op is None or op.organization_id != org_id:
                raise HTTPException(status_code=404, detail="Fleet operator not found")
        if payload.base_site_id:
            self.org.assert_site_in_org(organization_id=org_id, site_id=payload.base_site_id)
        row = Fleet(
            organization_id=org_id,
            operator_id=payload.operator_id,
            name=payload.name.strip(),
            code=payload.code.strip().upper(),
            base_site_id=payload.base_site_id,
            notes=payload.notes or "",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_fleet(row)
        self._commit_or_conflict(detail="Fleet code already exists in organization")
        self.repo.refresh(row)
        return self.fleet_out(row)

    def create_aircraft(
        self,
        payload: AircraftCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> AircraftOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        if self.repo.get_model(payload.model_id) is None:
            raise HTTPException(status_code=404, detail="Aircraft model not found")
        if self.repo.get_status(payload.status_code) is None:
            raise HTTPException(status_code=400, detail="Invalid aircraft status_code")
        if payload.fleet_id:
            fleet = self.repo.get_fleet(payload.fleet_id)
            if fleet is None or fleet.organization_id != org_id:
                raise HTTPException(status_code=404, detail="Fleet not found")
        if payload.operator_id:
            op = self.repo.get_operator(payload.operator_id)
            if op is None or op.organization_id != org_id:
                raise HTTPException(status_code=404, detail="Fleet operator not found")
        if payload.home_base_site_id:
            self.org.assert_site_in_org(organization_id=org_id, site_id=payload.home_base_site_id)

        mark = (payload.registration_mark or "").strip().upper() or None
        if mark and self.repo.get_registration_by_mark(mark):
            raise HTTPException(status_code=409, detail="Registration mark already exists")

        row = Aircraft(
            organization_id=org_id,
            model_id=payload.model_id,
            fleet_id=payload.fleet_id,
            operator_id=payload.operator_id,
            status_code=payload.status_code,
            serial_number=payload.serial_number.strip().upper(),
            manufacturer_serial=(payload.manufacturer_serial or "").strip().upper(),
            year_built=payload.year_built,
            home_base_site_id=payload.home_base_site_id,
            notes=payload.notes or "",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_aircraft(row)
        try:
            self.repo.flush()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail="Aircraft serial already exists in organization") from exc

        if mark:
            self.repo.add_registration(
                Registration(
                    organization_id=org_id,
                    aircraft_id=row.id,
                    registration_mark=mark,
                    country=(payload.registration_country or "").strip().upper(),
                    is_current="true",
                    effective_from=_utcnow(),
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
            )
        self._commit_or_conflict(detail="Aircraft or registration conflict")
        self.repo.refresh(row)
        return self.aircraft_out(row, current_mark=mark)

    def update_aircraft_status(
        self,
        aircraft_id: str,
        status_code: str,
        *,
        username: str,
        session_role: str,
    ) -> AircraftOut:
        row = self.repo.get_aircraft(aircraft_id)
        if row is None or row.status != "active":
            raise HTTPException(status_code=404, detail="Aircraft not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=row.organization_id)
        if self.repo.get_status(status_code) is None:
            raise HTTPException(status_code=400, detail="Invalid aircraft status_code")
        row.status_code = status_code
        row.updated_at = _utcnow()
        self._commit_or_conflict(detail="Unable to update aircraft status")
        self.repo.refresh(row)
        return self.aircraft_out(row)

    def create_registration(
        self,
        payload: RegistrationCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> RegistrationOut:
        aircraft = self.repo.get_aircraft(payload.aircraft_id)
        if aircraft is None or aircraft.status != "active":
            raise HTTPException(status_code=404, detail="Aircraft not found")
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id or aircraft.organization_id,
        )
        if aircraft.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Aircraft not found")

        mark = payload.registration_mark.strip().upper()
        if self.repo.get_registration_by_mark(mark):
            raise HTTPException(status_code=409, detail="Registration mark already exists")

        if payload.make_current:
            current = self.repo.get_current_registration(aircraft.id)
            if current is not None:
                current.is_current = "false"
                current.effective_to = _utcnow()
                current.updated_at = _utcnow()

        row = Registration(
            organization_id=org_id,
            aircraft_id=aircraft.id,
            registration_mark=mark,
            country=(payload.country or "").strip().upper(),
            is_current="true" if payload.make_current else "false",
            effective_from=_utcnow() if payload.make_current else None,
            notes=payload.notes or "",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_registration(row)
        self._commit_or_conflict(detail="Registration already exists")
        self.repo.refresh(row)
        return self.registration_out(row)

    def list_aircraft_for_org(
        self,
        *,
        organization_id: str,
        fleet_id: str | None = None,
        status_code: str | None = None,
    ) -> list[AircraftOut]:
        rows = self.repo.list_aircraft(
            organization_id=organization_id,
            fleet_id=fleet_id,
            status_code=status_code,
            with_registrations=True,
        )
        out: list[AircraftOut] = []
        for row in rows:
            current = next((r for r in row.registrations if _truthy(r.is_current) and r.status == "active"), None)
            out.append(self.aircraft_out(row, current_mark=current.registration_mark if current else None))
        return out
