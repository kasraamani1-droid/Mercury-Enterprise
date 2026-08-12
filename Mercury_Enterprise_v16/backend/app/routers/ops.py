from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..connectors.manager import connector_manager
from ..core.health import build_ops_health
from ..database import get_db
from ..ops import ResponseOrchestrationEngine
from ..security.authorization import has_permissions

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])


def get_response_orchestrator() -> ResponseOrchestrationEngine:
    """Reuse the application singleton from main (avoid a second orchestrator instance)."""
    from ..main import response_orchestrator

    return response_orchestrator


def _current_session(request: Request) -> dict:
    from ..main import _request_session_id, _validate_session

    session = _validate_session(_request_session_id(request))
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def require_ops_read(request: Request) -> dict:
    session = _current_session(request)
    if not has_permissions(str(session.get("role")), ("ops.read",)):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return session


def require_ops_coordinate(request: Request) -> dict:
    session = _current_session(request)
    if not has_permissions(str(session.get("role")), ("ops.coordinate",)):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return session


@router.get("/health")
def ops_health(
    db: Session = Depends(get_db),
    session: dict = Depends(require_ops_read),
) -> dict[str, Any]:
    return build_ops_health(db, connector_manager)


@router.post("/coordinate")
def coordinate(
    payload: dict[str, Any],
    orchestrator: ResponseOrchestrationEngine = Depends(get_response_orchestrator),
    session: dict = Depends(require_ops_coordinate),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    decision = orchestrator.coordinate(
        event_type=str(payload.get("event_type") or "unknown"),
        payload=payload.get("payload") if isinstance(payload.get("payload"), dict) else {},
        source="api",
    )
    record_audit(
        db,
        action="ops.coordinate",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="ops",
        target_id=str(decision.mission_id or decision.track_id or ""),
        source="api",
        outcome="success",
        origin="operator",
        details=str(payload.get("event_type") or "unknown"),
    )
    db.commit()
    return decision.to_dict()
