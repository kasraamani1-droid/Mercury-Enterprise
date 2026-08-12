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
    AircraftConfigurationOut,
    AtaChapterCreate,
    AtaChapterOut,
    CatalogItemCreate,
    CatalogItemOut,
    HistoryOut,
    InstallRequest,
    LifeLimitUpdate,
    RemoveRequest,
    SerializedComponentCreate,
    SerializedComponentOut,
    TimeCycleUpdate,
    TransferRequest,
)
from .service import ComponentService

logger = logging.getLogger("mercury.components")
router = APIRouter(prefix="/api/v1/components", tags=["components"])


def _session(request: Request) -> dict[str, datetime | str]:
    from ..main import require_session

    return require_session(request)


def require_component_read(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    if not has_permissions(str(session.get("role")), ("component.read",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return session


def require_component_manage(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    if not has_permissions(str(session.get("role")), ("component.manage",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Component management required")
    return session


def require_configuration_read(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    if not has_permissions(str(session.get("role")), ("configuration.read",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return session


def require_catalog_admin(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    username = str(session.get("operator", ""))
    record = operator_store.get(username)
    global_role = record["role"] if record else str(session.get("role", ""))
    if not has_permissions(global_role, ("admin.system",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Catalog management required")
    return session


def _svc(db: Session) -> ComponentService:
    return ComponentService(db)


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
        logger.exception("Failed to record component audit action=%s target=%s", action, target_id)


@router.get("/ata-chapters", response_model=list[AtaChapterOut])
def list_ata_chapters(
    db: Session = Depends(get_db),
    _: dict[str, datetime | str] = Depends(require_component_read),
) -> list[AtaChapterOut]:
    svc = _svc(db)
    return [svc.ata_out(r) for r in svc.repo.list_ata_chapters()]


@router.post("/ata-chapters", response_model=AtaChapterOut, status_code=201)
def create_ata_chapter(
    payload: AtaChapterCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_catalog_admin),
) -> AtaChapterOut:
    out = _svc(db).create_ata_chapter(payload)
    _audit(db, session, action="component.ata.create", target_type="ata_chapter", target_id=out.id, details=out.title)
    return out


@router.get("/catalog", response_model=list[CatalogItemOut])
def list_catalog(
    ata_chapter_id: str | None = None,
    component_type: str | None = None,
    db: Session = Depends(get_db),
    _: dict[str, datetime | str] = Depends(require_component_read),
) -> list[CatalogItemOut]:
    svc = _svc(db)
    return [
        svc.catalog_out(r)
        for r in svc.repo.list_catalog(ata_chapter_id=ata_chapter_id, component_type=component_type)
    ]


@router.post("/catalog", response_model=CatalogItemOut, status_code=201)
def create_catalog_item(
    payload: CatalogItemCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_catalog_admin),
) -> CatalogItemOut:
    out = _svc(db).create_catalog_item(payload)
    _audit(db, session, action="component.catalog.create", target_type="catalog_item", target_id=out.id, details=out.part_number)
    return out


@router.get("/serialized", response_model=list[SerializedComponentOut])
def list_serialized(
    organization_id: str | None = None,
    aircraft_id: str | None = None,
    component_status: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_component_read),
) -> list[SerializedComponentOut]:
    svc = _svc(db)
    org_id = svc.resolve_org_id(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        requested_org_id=organization_id,
    )
    rows = svc.repo.list_components(
        organization_id=org_id,
        aircraft_id=aircraft_id,
        component_status=component_status,
        with_catalog=True,
    )
    return [svc.component_out(r) for r in rows]


@router.get("/serialized/{component_id}", response_model=SerializedComponentOut)
def get_serialized(
    component_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_component_read),
) -> SerializedComponentOut:
    svc = _svc(db)
    row = svc._get_org_component(component_id, username=str(session["operator"]), session_role=str(session["role"]))
    return svc.component_out(row)


@router.post("/serialized", response_model=SerializedComponentOut, status_code=201)
def create_serialized(
    payload: SerializedComponentCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_component_manage),
) -> SerializedComponentOut:
    out = _svc(db).create_component(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="component.create",
        target_type="serialized_component",
        target_id=out.id,
        details=out.serial_number,
        organization_id=out.organization_id,
    )
    return out


@router.post("/serialized/{component_id}/install", response_model=SerializedComponentOut)
def install_component(
    component_id: str,
    payload: InstallRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_component_manage),
) -> SerializedComponentOut:
    out = _svc(db).install(
        component_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="component.install",
        target_type="serialized_component",
        target_id=out.id,
        details=f"{payload.aircraft_id}:{payload.position}",
        organization_id=out.organization_id,
    )
    return out


@router.post("/serialized/{component_id}/remove", response_model=SerializedComponentOut)
def remove_component(
    component_id: str,
    payload: RemoveRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_component_manage),
) -> SerializedComponentOut:
    out = _svc(db).remove(
        component_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="component.remove",
        target_type="serialized_component",
        target_id=out.id,
        details=payload.destination_status,
        organization_id=out.organization_id,
    )
    return out


@router.post("/serialized/{component_id}/transfer", response_model=SerializedComponentOut)
def transfer_component(
    component_id: str,
    payload: TransferRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_component_manage),
) -> SerializedComponentOut:
    out = _svc(db).transfer(
        component_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="component.transfer",
        target_type="serialized_component",
        target_id=out.id,
        details=payload.to_status,
        organization_id=out.organization_id,
    )
    return out


@router.patch("/serialized/{component_id}/life-limits", response_model=SerializedComponentOut)
def update_life_limits(
    component_id: str,
    payload: LifeLimitUpdate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_component_manage),
) -> SerializedComponentOut:
    out = _svc(db).update_life_limits(
        component_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="component.life_limit",
        target_type="serialized_component",
        target_id=out.id,
        details=str(payload.model_dump()),
        organization_id=out.organization_id,
    )
    return out


@router.patch("/serialized/{component_id}/time-cycles", response_model=SerializedComponentOut)
def update_time_cycles(
    component_id: str,
    payload: TimeCycleUpdate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_component_manage),
) -> SerializedComponentOut:
    out = _svc(db).update_time_cycles(
        component_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="component.time_cycle",
        target_type="serialized_component",
        target_id=out.id,
        details=str(payload.model_dump()),
        organization_id=out.organization_id,
    )
    return out


@router.get("/serialized/{component_id}/history", response_model=list[HistoryOut])
def component_history(
    component_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_component_read),
) -> list[HistoryOut]:
    svc = _svc(db)
    row = svc._get_org_component(component_id, username=str(session["operator"]), session_role=str(session["role"]))
    history = svc.repo.list_history(organization_id=row.organization_id, component_id=row.id)
    return [svc.history_out(h) for h in history]


@router.get("/history", response_model=list[HistoryOut])
def list_history(
    organization_id: str | None = None,
    aircraft_id: str | None = None,
    component_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_component_read),
) -> list[HistoryOut]:
    svc = _svc(db)
    org_id = svc.resolve_org_id(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        requested_org_id=organization_id,
    )
    rows = svc.repo.list_history(
        organization_id=org_id,
        aircraft_id=aircraft_id,
        component_id=component_id,
        limit=limit,
    )
    return [svc.history_out(r) for r in rows]


@router.get("/aircraft/{aircraft_id}/configuration", response_model=AircraftConfigurationOut)
def aircraft_configuration(
    aircraft_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_configuration_read),
) -> AircraftConfigurationOut:
    return _svc(db).aircraft_configuration(
        aircraft_id,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
