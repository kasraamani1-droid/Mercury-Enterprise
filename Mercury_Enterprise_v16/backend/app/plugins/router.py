"""Program 16 — Mercury Plugin Platform HTTP API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from ..shared import ActorContext
from .schemas import (
    DashboardCreate,
    DashboardOut,
    InstallationCreate,
    InstallationOut,
    PluginOut,
    PluginsOverviewOut,
)
from .service import PluginService

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])
Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_plugins_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("plugins.read", "connect.read", "platform.read", "org.read"),
        any_of=True,
        detail="Plugins read required",
    )
    return session


def require_plugins_manage(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("plugins.manage", "connect.manage", "platform.manage"),
        any_of=True,
        detail="Plugins manage required",
    )
    return session


def _actor(session: Session_) -> ActorContext:
    return ActorContext(
        username=str(session["operator"]),
        role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )


@router.get("/overview", response_model=PluginsOverviewOut)
def overview(
    organization_id: str | None = None,
    session: Session_ = Depends(require_plugins_read),
    db: Session = Depends(get_db),
) -> PluginsOverviewOut:
    return PluginService(db).overview(_actor(session), organization_id)


@router.get("/catalog", response_model=list[PluginOut])
def list_catalog(
    category: str | None = None,
    session: Session_ = Depends(require_plugins_read),
    db: Session = Depends(get_db),
) -> list[PluginOut]:
    _ = session
    return [PluginOut.model_validate(r) for r in PluginService(db).list_plugins(category=category)]


@router.get("/catalog/{code}", response_model=PluginOut)
def get_plugin(
    code: str,
    session: Session_ = Depends(require_plugins_read),
    db: Session = Depends(get_db),
) -> PluginOut:
    _ = session
    return PluginOut.model_validate(PluginService(db).get_plugin(code))


@router.get("/installations", response_model=list[InstallationOut])
def list_installations(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_plugins_read),
    db: Session = Depends(get_db),
) -> list[InstallationOut]:
    rows = PluginService(db).list_installations(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )
    return [InstallationOut.model_validate(r) for r in rows]


@router.post("/installations", response_model=InstallationOut, status_code=201)
def install_plugin(
    payload: InstallationCreate,
    session: Session_ = Depends(require_plugins_manage),
    db: Session = Depends(get_db),
) -> InstallationOut:
    row = PluginService(db).install(_actor(session), **payload.model_dump())
    return InstallationOut.model_validate(row)


@router.get("/dashboards", response_model=list[DashboardOut])
def list_dashboards(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_plugins_read),
    db: Session = Depends(get_db),
) -> list[DashboardOut]:
    rows = PluginService(db).list_dashboards(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )
    return [DashboardOut.model_validate(r) for r in rows]


@router.post("/dashboards", response_model=DashboardOut, status_code=201)
def create_dashboard(
    payload: DashboardCreate,
    session: Session_ = Depends(require_plugins_manage),
    db: Session = Depends(get_db),
) -> DashboardOut:
    row = PluginService(db).create_dashboard(_actor(session), **payload.model_dump())
    return DashboardOut.model_validate(row)
