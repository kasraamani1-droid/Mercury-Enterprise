"""Mercury Connect HTTP API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from ..shared import ActorContext
from .schemas import BindingCreate, BindingOut, ConnectOverviewOut, ConnectorOut
from .service import ConnectService

router = APIRouter(prefix="/api/v1/connect", tags=["connect"])
Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_connect_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("connect.read", "platform.read", "org.read"),
        any_of=True,
        detail="Connect read required",
    )
    return session


def require_connect_manage(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("connect.manage", "platform.manage"),
        any_of=True,
        detail="Connect manage required",
    )
    return session


def _actor(session: Session_) -> ActorContext:
    return ActorContext(
        username=str(session["operator"]),
        role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )


@router.get("/overview", response_model=ConnectOverviewOut)
def overview(
    organization_id: str | None = None,
    session: Session_ = Depends(require_connect_read),
    db: Session = Depends(get_db),
) -> ConnectOverviewOut:
    return ConnectService(db).overview(_actor(session), organization_id=organization_id)


@router.get("/connectors", response_model=list[ConnectorOut])
def list_connectors(
    category: str | None = None,
    session: Session_ = Depends(require_connect_read),
    db: Session = Depends(get_db),
) -> list[ConnectorOut]:
    _ = session
    return ConnectService(db).list_connectors(category=category)


@router.get("/connectors/{code}", response_model=ConnectorOut)
def get_connector(
    code: str,
    session: Session_ = Depends(require_connect_read),
    db: Session = Depends(get_db),
) -> ConnectorOut:
    _ = session
    return ConnectService(db).get_connector(code)


@router.post("/bindings", response_model=BindingOut, status_code=201)
def create_binding(
    payload: BindingCreate,
    session: Session_ = Depends(require_connect_manage),
    db: Session = Depends(get_db),
) -> BindingOut:
    return ConnectService(db).create_binding(payload, _actor(session))


@router.get("/bindings", response_model=list[BindingOut])
def list_bindings(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_connect_read),
    db: Session = Depends(get_db),
) -> list[BindingOut]:
    return ConnectService(db).list_bindings(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )
