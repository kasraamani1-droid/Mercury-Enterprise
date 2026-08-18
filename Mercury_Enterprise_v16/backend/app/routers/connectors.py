from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..connectors.manager import connector_manager
from ..connectors.models import ConnectorHealth, ConnectorHealthEvent, ConnectorRecord, NormalizedObservation
from ..database import get_db
from ..events.bus import event_bus
from ..events.models import PlatformEvent
from ..security.runtime_authz import require_allowed

router = APIRouter(prefix="/api/v1", tags=["connectors"])


def _current_session(request: Request) -> dict:
    from ..main import _request_session_id, _validate_session

    session = _validate_session(_request_session_id(request))
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def require_connectors_read(request: Request, db: Session = Depends(get_db)) -> dict:
    session = _current_session(request)
    require_allowed(db, session, ("connectors.read",), detail="Insufficient permissions")
    return session


def require_connectors_manage(request: Request, db: Session = Depends(get_db)) -> dict:
    session = _current_session(request)
    require_allowed(db, session, ("connectors.manage",), detail="Insufficient permissions")
    return session


def _audit_connector(db: Session, session: dict, *, action: str, connector_id: str, details: str = "") -> None:
    record_audit(
        db,
        action=action,
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="connector",
        target_id=connector_id,
        source="api",
        outcome="success",
        origin="operator",
        details=details,
    )
    db.commit()


@router.get("/connectors", response_model=list[ConnectorRecord])
def list_connectors(session: dict = Depends(require_connectors_read)):
    records = connector_manager.list_records()
    # Prefer site-tagged connectors; include unscoped for compatibility.
    site_id = str(session["site_id"])
    scoped = [item for item in records if item.site_id in {None, site_id}]
    return scoped or records


@router.get("/connectors/{connector_id}/health", response_model=ConnectorHealth)
async def connector_health(connector_id: str, _: dict = Depends(require_connectors_read)):
    connector = connector_manager.get(connector_id)
    if connector is None:
        raise HTTPException(404, "Connector not found")
    return await connector.health()


@router.get("/connectors/{connector_id}/health-history", response_model=list[ConnectorHealthEvent])
def connector_health_history(
    connector_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    _: dict = Depends(require_connectors_read),
):
    if connector_manager.get(connector_id) is None:
        raise HTTPException(404, "Connector not found")
    return connector_manager.health_history(connector_id, limit=limit)


@router.post("/connectors/{connector_id}/start", response_model=ConnectorRecord)
async def start_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    session: dict = Depends(require_connectors_manage),
):
    try:
        record = await connector_manager.start(connector_id, actor=str(session["operator"]))
    except KeyError as exc:
        raise HTTPException(404, "Connector not found") from exc
    _audit_connector(db, session, action="connector.start", connector_id=connector_id)
    return record


@router.post("/connectors/{connector_id}/stop", response_model=ConnectorRecord)
async def stop_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    session: dict = Depends(require_connectors_manage),
):
    try:
        record = await connector_manager.stop(connector_id, actor=str(session["operator"]))
    except KeyError as exc:
        raise HTTPException(404, "Connector not found") from exc
    _audit_connector(db, session, action="connector.stop", connector_id=connector_id)
    return record


@router.post("/connectors/{connector_id}/recover", response_model=ConnectorRecord)
async def recover_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    session: dict = Depends(require_connectors_manage),
):
    try:
        record = await connector_manager.recover(connector_id, actor=str(session["operator"]))
    except KeyError as exc:
        raise HTTPException(404, "Connector not found") from exc
    _audit_connector(db, session, action="connector.recover", connector_id=connector_id)
    return record


@router.post("/connectors/{connector_id}/poll", response_model=list[NormalizedObservation])
async def poll_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    session: dict = Depends(require_connectors_manage),
):
    try:
        observations = await connector_manager.poll(connector_id, actor=str(session["operator"]))
    except KeyError as exc:
        raise HTTPException(404, "Connector not found") from exc
    except Exception as exc:
        record_audit(
            db,
            action="connector.poll",
            actor=str(session["operator"]),
            actor_role=str(session["role"]),
            organization_id=str(session["organization_id"]),
            site_id=str(session["site_id"]),
            target_type="connector",
            target_id=connector_id,
            source="api",
            outcome="failed",
            origin="operator",
            details=str(exc),
        )
        db.commit()
        raise HTTPException(status_code=502, detail=f"Connector poll failed: {exc}") from exc
    _audit_connector(db, session, action="connector.poll", connector_id=connector_id, details=f"observations={len(observations)}")
    return observations


@router.get("/events", response_model=list[PlatformEvent])
def recent_events(limit: int = Query(default=50, ge=1, le=500), _: dict = Depends(require_connectors_read)):
    return event_bus.recent(limit)
