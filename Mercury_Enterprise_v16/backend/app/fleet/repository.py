from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

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


class FleetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # Manufacturers / models / statuses (catalog)
    def list_manufacturers(self, *, active_only: bool = True) -> list[Manufacturer]:
        stmt = select(Manufacturer).order_by(Manufacturer.name)
        if active_only:
            stmt = stmt.where(Manufacturer.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_manufacturer(self, manufacturer_id: str) -> Manufacturer | None:
        return self.db.get(Manufacturer, manufacturer_id)

    def get_manufacturer_by_code(self, code: str) -> Manufacturer | None:
        return self.db.scalar(select(Manufacturer).where(Manufacturer.code == code.upper()))

    def add_manufacturer(self, row: Manufacturer) -> Manufacturer:
        self.db.add(row)
        return row

    def list_models(self, *, manufacturer_id: str | None = None, active_only: bool = True) -> list[AircraftModel]:
        stmt = select(AircraftModel).order_by(AircraftModel.name)
        if manufacturer_id:
            stmt = stmt.where(AircraftModel.manufacturer_id == manufacturer_id)
        if active_only:
            stmt = stmt.where(AircraftModel.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_model(self, model_id: str) -> AircraftModel | None:
        return self.db.get(AircraftModel, model_id)

    def add_model(self, row: AircraftModel) -> AircraftModel:
        self.db.add(row)
        return row

    def list_families(self, *, manufacturer_id: str | None = None, active_only: bool = True) -> list[AircraftFamily]:
        stmt = select(AircraftFamily).order_by(AircraftFamily.name)
        if manufacturer_id:
            stmt = stmt.where(AircraftFamily.manufacturer_id == manufacturer_id)
        if active_only:
            stmt = stmt.where(AircraftFamily.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_family(self, family_id: str) -> AircraftFamily | None:
        return self.db.get(AircraftFamily, family_id)

    def add_family(self, row: AircraftFamily) -> AircraftFamily:
        self.db.add(row)
        return row

    def list_statuses(self, *, active_only: bool = True) -> list[AircraftStatus]:
        stmt = select(AircraftStatus).order_by(AircraftStatus.sort_order, AircraftStatus.code)
        if active_only:
            stmt = stmt.where(AircraftStatus.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_status(self, code: str) -> AircraftStatus | None:
        return self.db.get(AircraftStatus, code)

    def add_status(self, row: AircraftStatus) -> AircraftStatus:
        self.db.add(row)
        return row

    # Operators / fleets / aircraft / registrations (tenant)
    def list_operators(self, *, organization_id: str, active_only: bool = True) -> list[FleetOperator]:
        stmt = (
            select(FleetOperator)
            .where(FleetOperator.organization_id == organization_id)
            .order_by(FleetOperator.name)
        )
        if active_only:
            stmt = stmt.where(FleetOperator.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_operator(self, operator_id: str) -> FleetOperator | None:
        return self.db.get(FleetOperator, operator_id)

    def add_operator(self, row: FleetOperator) -> FleetOperator:
        self.db.add(row)
        return row

    def list_fleets(self, *, organization_id: str, active_only: bool = True) -> list[Fleet]:
        stmt = select(Fleet).where(Fleet.organization_id == organization_id).order_by(Fleet.name)
        if active_only:
            stmt = stmt.where(Fleet.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_fleet(self, fleet_id: str) -> Fleet | None:
        return self.db.get(Fleet, fleet_id)

    def add_fleet(self, row: Fleet) -> Fleet:
        self.db.add(row)
        return row

    def count_aircraft_by_fleet(self, *, organization_id: str) -> dict[str, int]:
        rows = self.db.execute(
            select(Aircraft.fleet_id, func.count())
            .where(
                Aircraft.organization_id == organization_id,
                Aircraft.status == "active",
                Aircraft.fleet_id.is_not(None),
            )
            .group_by(Aircraft.fleet_id)
        ).all()
        return {str(fleet_id): int(count) for fleet_id, count in rows if fleet_id}

    def count_aircraft_in_fleet(self, fleet_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(Aircraft).where(
                    Aircraft.fleet_id == fleet_id,
                    Aircraft.status == "active",
                )
            )
            or 0
        )

    def list_aircraft(
        self,
        *,
        organization_id: str,
        fleet_id: str | None = None,
        status_code: str | None = None,
        active_only: bool = True,
        with_registrations: bool = False,
    ) -> list[Aircraft]:
        stmt = select(Aircraft).where(Aircraft.organization_id == organization_id).order_by(Aircraft.serial_number)
        if with_registrations:
            stmt = stmt.options(joinedload(Aircraft.registrations))
        if fleet_id:
            stmt = stmt.where(Aircraft.fleet_id == fleet_id)
        if status_code:
            stmt = stmt.where(Aircraft.status_code == status_code)
        if active_only:
            stmt = stmt.where(Aircraft.status == "active")
        return list(self.db.scalars(stmt).unique().all())

    def get_aircraft(self, aircraft_id: str, *, with_registrations: bool = False) -> Aircraft | None:
        if not with_registrations:
            return self.db.get(Aircraft, aircraft_id)
        return self.db.scalar(
            select(Aircraft)
            .where(Aircraft.id == aircraft_id)
            .options(joinedload(Aircraft.registrations))
        )

    def add_aircraft(self, row: Aircraft) -> Aircraft:
        self.db.add(row)
        return row

    def count_operational_aircraft(self, *, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(Aircraft)
                .join(AircraftStatus, Aircraft.status_code == AircraftStatus.code)
                .where(
                    Aircraft.organization_id == organization_id,
                    Aircraft.status == "active",
                    AircraftStatus.is_operational == "true",
                )
            )
            or 0
        )

    def list_registrations(
        self,
        *,
        organization_id: str,
        aircraft_id: str | None = None,
        current_only: bool = False,
    ) -> list[Registration]:
        stmt = (
            select(Registration)
            .where(Registration.organization_id == organization_id)
            .order_by(Registration.created_at.desc())
        )
        if aircraft_id:
            stmt = stmt.where(Registration.aircraft_id == aircraft_id)
        if current_only:
            stmt = stmt.where(Registration.is_current == "true")
        return list(self.db.scalars(stmt).all())

    def get_registration_by_mark(self, registration_mark: str) -> Registration | None:
        return self.db.scalar(
            select(Registration).where(Registration.registration_mark == registration_mark.upper())
        )

    def get_current_registration(self, aircraft_id: str) -> Registration | None:
        return self.db.scalar(
            select(Registration).where(
                Registration.aircraft_id == aircraft_id,
                Registration.is_current == "true",
                Registration.status == "active",
            )
        )

    def add_registration(self, row: Registration) -> Registration:
        self.db.add(row)
        return row

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)

    def flush(self) -> None:
        self.db.flush()
