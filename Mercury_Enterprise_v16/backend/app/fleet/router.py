from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..database import get_db
from ..security.authorization import has_permissions
from ..security.operators import operator_store
from .schemas import (
    AircraftCreate,
    AircraftFamilyOut,
    AircraftModelCreate,
    AircraftModelOut,
    AircraftOut,
    AircraftStatusOut,
    AircraftStatusUpdate,
    FleetCreate,
    FleetOperatorCreate,
    FleetOperatorOut,
    FleetOut,
    ManufacturerCreate,
    ManufacturerOut,
    RegistrationCreate,
    RegistrationOut,
)
from .service import FleetService

logger = logging.getLogger("mercury.fleet")
router = APIRouter(prefix="/api/v1/fleet", tags=["fleet"])


def _session(request: Request) -> dict[str, datetime | str]:
    from ..main import require_session

    return require_session(request)


def require_fleet_read(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    if not has_permissions(str(session.get("role")), ("fleet.read",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return session


def require_fleet_manage(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    if not has_permissions(str(session.get("role")), ("fleet.manage",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Fleet management required")
    return session


def require_fleet_catalog(request: Request) -> dict[str, datetime | str]:
    """Manufacturer/model catalog writes require platform admin (login directory)."""
    session = _session(request)
    username = str(session.get("operator", ""))
    record = operator_store.get(username)
    global_role = record["role"] if record else str(session.get("role", ""))
    if not has_permissions(global_role, ("admin.system",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Catalog management required")
    return session


def _svc(db: Session) -> FleetService:
    return FleetService(db)


def _safe_commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _audit(
    db: Session,
    session: dict[str, datetime | str],
    *,
    action: str,
    target_type: str,
    target_id: str,
    details: str = "",
    organization_id: str | None = None,
) -> None:
    try:
        record_audit(
            db,
            action=action,
            actor=str(session["operator"]),
            actor_role=str(session["role"]),
            organization_id=organization_id or str(session["organization_id"]),
            site_id=str(session["site_id"]),
            target_type=target_type,
            target_id=target_id,
            source="api",
            outcome="success",
            origin="operator",
            details=details,
        )
        _safe_commit(db)
    except Exception:
        db.rollback()
        logger.exception("Failed to record fleet audit action=%s target=%s", action, target_id)


@router.get("/manufacturers", response_model=list[ManufacturerOut])
def list_manufacturers(
    db: Session = Depends(get_db),
    _: dict[str, datetime | str] = Depends(require_fleet_read),
) -> list[ManufacturerOut]:
    svc = _svc(db)
    return [svc.manufacturer_out(r) for r in svc.repo.list_manufacturers()]


@router.post("/manufacturers", response_model=ManufacturerOut, status_code=201)
def create_manufacturer(
    payload: ManufacturerCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_catalog),
) -> ManufacturerOut:
    out = _svc(db).create_manufacturer(payload)
    _audit(db, session, action="fleet.manufacturer.create", target_type="manufacturer", target_id=out.id, details=out.code)
    return out


@router.get("/families", response_model=list[AircraftFamilyOut])
def list_families(
    manufacturer_id: str | None = None,
    db: Session = Depends(get_db),
    _: dict[str, datetime | str] = Depends(require_fleet_read),
) -> list[AircraftFamilyOut]:
    svc = _svc(db)
    return [svc.family_out(r) for r in svc.repo.list_families(manufacturer_id=manufacturer_id)]


@router.get("/models", response_model=list[AircraftModelOut])
def list_models(
    manufacturer_id: str | None = None,
    db: Session = Depends(get_db),
    _: dict[str, datetime | str] = Depends(require_fleet_read),
) -> list[AircraftModelOut]:
    svc = _svc(db)
    return [svc.model_out(r) for r in svc.repo.list_models(manufacturer_id=manufacturer_id)]


@router.post("/models", response_model=AircraftModelOut, status_code=201)
def create_model(
    payload: AircraftModelCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_catalog),
) -> AircraftModelOut:
    out = _svc(db).create_model(payload)
    _audit(db, session, action="fleet.model.create", target_type="aircraft_model", target_id=out.id, details=out.code)
    return out


@router.get("/statuses", response_model=list[AircraftStatusOut])
def list_statuses(
    db: Session = Depends(get_db),
    _: dict[str, datetime | str] = Depends(require_fleet_read),
) -> list[AircraftStatusOut]:
    svc = _svc(db)
    return [svc.status_out(r) for r in svc.repo.list_statuses()]


@router.get("/operators", response_model=list[FleetOperatorOut])
def list_operators(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_read),
) -> list[FleetOperatorOut]:
    svc = _svc(db)
    org_id = svc.resolve_org_id(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        requested_org_id=organization_id,
    )
    return [svc.operator_out(r) for r in svc.repo.list_operators(organization_id=org_id)]


@router.post("/operators", response_model=FleetOperatorOut, status_code=201)
def create_operator(
    payload: FleetOperatorCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_manage),
) -> FleetOperatorOut:
    out = _svc(db).create_operator(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="fleet.operator.create",
        target_type="fleet_operator",
        target_id=out.id,
        details=out.code,
        organization_id=out.organization_id,
    )
    return out


@router.get("/fleets", response_model=list[FleetOut])
def list_fleets(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_read),
) -> list[FleetOut]:
    svc = _svc(db)
    org_id = svc.resolve_org_id(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        requested_org_id=organization_id,
    )
    return svc.list_fleets_for_org(org_id)


@router.post("/fleets", response_model=FleetOut, status_code=201)
def create_fleet(
    payload: FleetCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_manage),
) -> FleetOut:
    out = _svc(db).create_fleet(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="fleet.fleet.create",
        target_type="fleet",
        target_id=out.id,
        details=out.code,
        organization_id=out.organization_id,
    )
    return out


@router.get("/aircraft", response_model=list[AircraftOut])
def list_aircraft(
    organization_id: str | None = None,
    fleet_id: str | None = None,
    status_code: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_read),
) -> list[AircraftOut]:
    svc = _svc(db)
    org_id = svc.resolve_org_id(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        requested_org_id=organization_id,
    )
    return svc.list_aircraft_for_org(organization_id=org_id, fleet_id=fleet_id, status_code=status_code)


@router.get("/aircraft/{aircraft_id}", response_model=AircraftOut)
def get_aircraft(
    aircraft_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_read),
) -> AircraftOut:
    svc = _svc(db)
    row = svc.repo.get_aircraft(aircraft_id, with_registrations=True)
    if row is None or row.status != "active":
        raise HTTPException(status_code=404, detail="Aircraft not found")
    svc.assert_org_access(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        organization_id=row.organization_id,
    )
    current = next((r for r in row.registrations if r.is_current == "true" and r.status == "active"), None)
    return svc.aircraft_out(row, current_mark=current.registration_mark if current else None)


@router.post("/aircraft", response_model=AircraftOut, status_code=201)
def create_aircraft(
    payload: AircraftCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_manage),
) -> AircraftOut:
    out = _svc(db).create_aircraft(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="fleet.aircraft.create",
        target_type="aircraft",
        target_id=out.id,
        details=out.serial_number,
        organization_id=out.organization_id,
    )
    return out


@router.patch("/aircraft/{aircraft_id}/status", response_model=AircraftOut)
def update_aircraft_status(
    aircraft_id: str,
    payload: AircraftStatusUpdate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_manage),
) -> AircraftOut:
    out = _svc(db).update_aircraft_status(
        aircraft_id,
        payload.status_code,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="fleet.aircraft.status",
        target_type="aircraft",
        target_id=out.id,
        details=payload.status_code,
        organization_id=out.organization_id,
    )
    return out


@router.get("/registrations", response_model=list[RegistrationOut])
def list_registrations(
    organization_id: str | None = None,
    aircraft_id: str | None = None,
    current_only: bool = False,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_read),
) -> list[RegistrationOut]:
    svc = _svc(db)
    org_id = svc.resolve_org_id(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        requested_org_id=organization_id,
    )
    rows = svc.repo.list_registrations(
        organization_id=org_id,
        aircraft_id=aircraft_id,
        current_only=current_only,
    )
    return [svc.registration_out(r) for r in rows]


@router.post("/registrations", response_model=RegistrationOut, status_code=201)
def create_registration(
    payload: RegistrationCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_fleet_manage),
) -> RegistrationOut:
    out = _svc(db).create_registration(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="fleet.registration.create",
        target_type="registration",
        target_id=out.id,
        details=out.registration_mark,
        organization_id=out.organization_id,
    )
    return out
