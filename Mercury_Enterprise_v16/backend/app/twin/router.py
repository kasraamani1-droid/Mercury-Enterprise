"""Program 15 — Mercury Digital Twin HTTP API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from ..shared import ActorContext
from .schemas import (
    ConfigurationCreate,
    ConfigurationOut,
    HistoryCreate,
    HistoryOut,
    LifecycleTransition,
    RelationshipOut,
    ReliabilityCreate,
    ReliabilityOut,
    TwinCreate,
    TwinDetailOut,
    TwinOut,
    TwinOverviewOut,
    TwinSearchResponse,
)
from .service import TwinService

router = APIRouter(prefix="/api/v1/twin", tags=["twin"])
Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_twin_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("twin.read", "fabric.read", "platform.read", "org.read"),
        any_of=True,
        detail="Twin read required",
    )
    return session


def require_twin_manage(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("twin.manage", "fabric.manage", "platform.manage"),
        any_of=True,
        detail="Twin manage required",
    )
    return session


def _actor(session: Session_) -> ActorContext:
    return ActorContext(
        username=str(session["operator"]),
        role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )


@router.get("/overview", response_model=TwinOverviewOut)
def overview(
    organization_id: str | None = None,
    session: Session_ = Depends(require_twin_read),
    db: Session = Depends(get_db),
) -> TwinOverviewOut:
    return TwinService(db).overview(_actor(session), organization_id)


@router.get("/search", response_model=TwinSearchResponse)
def search(
    q: str = "",
    twin_type: str | None = None,
    organization_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_twin_read),
    db: Session = Depends(get_db),
) -> TwinSearchResponse:
    return TwinService(db).search(
        _actor(session),
        q=q,
        twin_type=twin_type,
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )


@router.get("/twins", response_model=list[TwinOut])
def list_twins(
    organization_id: str | None = None,
    twin_type: str | None = None,
    lifecycle_state: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_twin_read),
    db: Session = Depends(get_db),
) -> list[TwinOut]:
    rows = TwinService(db).list_twins(
        _actor(session),
        organization_id=organization_id,
        twin_type=twin_type,
        lifecycle_state=lifecycle_state,
        limit=limit,
        offset=offset,
    )
    return [TwinOut.model_validate(r) for r in rows]


@router.post("/twins", response_model=TwinOut, status_code=201)
def create_twin(
    payload: TwinCreate,
    session: Session_ = Depends(require_twin_manage),
    db: Session = Depends(get_db),
) -> TwinOut:
    row = TwinService(db).create_twin(_actor(session), **payload.model_dump())
    return TwinOut.model_validate(row)


@router.get("/twins/by-uuid/{twin_uuid}", response_model=TwinDetailOut)
def get_twin_by_uuid(
    twin_uuid: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_twin_read),
    db: Session = Depends(get_db),
) -> TwinDetailOut:
    return TwinService(db).get_by_uuid(_actor(session), twin_uuid, organization_id)


@router.get("/twins/{twin_id}", response_model=TwinDetailOut)
def get_twin(
    twin_id: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_twin_read),
    db: Session = Depends(get_db),
) -> TwinDetailOut:
    return TwinService(db).get_twin(_actor(session), twin_id, organization_id)


@router.get("/twins/{twin_id}/passport")
def twin_passport(
    twin_id: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_twin_read),
    db: Session = Depends(get_db),
) -> dict:
    return TwinService(db).passport_view(_actor(session), twin_id, organization_id)


@router.post("/twins/{twin_id}/lifecycle", response_model=TwinOut)
def twin_lifecycle(
    twin_id: str,
    payload: LifecycleTransition,
    session: Session_ = Depends(require_twin_manage),
    db: Session = Depends(get_db),
) -> TwinOut:
    row = TwinService(db).transition_lifecycle(
        _actor(session),
        twin_id,
        to_state=payload.to_state,
        summary=payload.summary,
        related_ref=payload.related_ref,
        organization_id=payload.organization_id,
    )
    return TwinOut.model_validate(row)


@router.get("/twins/{twin_id}/history", response_model=list[HistoryOut])
def list_history(
    twin_id: str,
    organization_id: str | None = None,
    history_kind: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_twin_read),
    db: Session = Depends(get_db),
) -> list[HistoryOut]:
    rows = TwinService(db).list_history(
        _actor(session),
        twin_id,
        organization_id=organization_id,
        history_kind=history_kind,
        limit=limit,
        offset=offset,
    )
    return [HistoryOut.model_validate(r) for r in rows]


@router.post("/twins/{twin_id}/history", response_model=HistoryOut, status_code=201)
def append_history(
    twin_id: str,
    payload: HistoryCreate,
    session: Session_ = Depends(require_twin_manage),
    db: Session = Depends(get_db),
) -> HistoryOut:
    data = payload.model_dump()
    org = data.pop("organization_id", None)
    row = TwinService(db).append_history(
        _actor(session), twin_id, organization_id=org, **data
    )
    return HistoryOut.model_validate(row)


@router.get("/twins/{twin_id}/configurations", response_model=list[ConfigurationOut])
def list_configurations(
    twin_id: str,
    organization_id: str | None = None,
    baseline: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_twin_read),
    db: Session = Depends(get_db),
) -> list[ConfigurationOut]:
    rows = TwinService(db).list_configurations(
        _actor(session),
        twin_id,
        organization_id=organization_id,
        baseline=baseline,
        limit=limit,
        offset=offset,
    )
    return [ConfigurationOut.model_validate(r) for r in rows]


@router.post("/twins/{twin_id}/configurations", response_model=ConfigurationOut, status_code=201)
def create_configuration(
    twin_id: str,
    payload: ConfigurationCreate,
    session: Session_ = Depends(require_twin_manage),
    db: Session = Depends(get_db),
) -> ConfigurationOut:
    data = payload.model_dump()
    org = data.pop("organization_id", None)
    row = TwinService(db).create_configuration(
        _actor(session), twin_id, organization_id=org, **data
    )
    return ConfigurationOut.model_validate(row)


@router.get("/twins/{twin_id}/reliability", response_model=list[ReliabilityOut])
def list_reliability(
    twin_id: str,
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_twin_read),
    db: Session = Depends(get_db),
) -> list[ReliabilityOut]:
    rows = TwinService(db).list_reliability(
        _actor(session), twin_id, organization_id=organization_id, limit=limit, offset=offset
    )
    return [ReliabilityOut.model_validate(r) for r in rows]


@router.post("/twins/{twin_id}/reliability", response_model=ReliabilityOut, status_code=201)
def create_reliability(
    twin_id: str,
    payload: ReliabilityCreate,
    session: Session_ = Depends(require_twin_manage),
    db: Session = Depends(get_db),
) -> ReliabilityOut:
    data = payload.model_dump()
    org = data.pop("organization_id", None)
    row = TwinService(db).create_reliability(
        _actor(session), twin_id, organization_id=org, **data
    )
    return ReliabilityOut.model_validate(row)


@router.get("/twins/{twin_id}/relationships", response_model=RelationshipOut)
def twin_relationships(
    twin_id: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_twin_read),
    db: Session = Depends(get_db),
) -> RelationshipOut:
    return TwinService(db).relationships(_actor(session), twin_id, organization_id)
