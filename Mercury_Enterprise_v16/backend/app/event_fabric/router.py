"""Program 17 — Enterprise Event Fabric HTTP API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from ..shared import ActorContext
from .schemas import (
    DeadLetterOut,
    EventFabricOverviewOut,
    EventTypeOut,
    PublishEventIn,
    ReplayOut,
    ReplayRequest,
    StoredEventOut,
    SubscriptionCreate,
    SubscriptionOut,
)
from .service import EventFabricService

router = APIRouter(prefix="/api/v1/event-fabric", tags=["event-fabric"])
Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_ef_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("event_fabric.read", "platform.read", "fabric.read", "org.read"),
        any_of=True,
        detail="Event Fabric read required",
    )
    return session


def require_ef_manage(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("event_fabric.manage", "platform.manage"),
        any_of=True,
        detail="Event Fabric manage required",
    )
    return session


def _actor(session: Session_) -> ActorContext:
    return ActorContext(
        username=str(session["operator"]),
        role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )


@router.get("/overview", response_model=EventFabricOverviewOut)
def overview(
    organization_id: str | None = None,
    session: Session_ = Depends(require_ef_read),
    db: Session = Depends(get_db),
) -> EventFabricOverviewOut:
    return EventFabricService(db).overview(_actor(session), organization_id)


@router.get("/catalog", response_model=list[EventTypeOut])
def list_catalog(
    family: str | None = None,
    session: Session_ = Depends(require_ef_read),
    db: Session = Depends(get_db),
) -> list[EventTypeOut]:
    _ = session
    return [EventTypeOut.model_validate(r) for r in EventFabricService(db).list_catalog(family=family)]


@router.post("/events", response_model=StoredEventOut, status_code=201)
def publish_event(
    payload: PublishEventIn,
    session: Session_ = Depends(require_ef_manage),
    db: Session = Depends(get_db),
) -> StoredEventOut:
    data = payload.model_dump()
    org = data.pop("organization_id", None)
    data.pop("actor", None)  # actor comes from session ActorContext
    row = EventFabricService(db).publish(_actor(session), organization_id=org, **data)
    return StoredEventOut.model_validate(row)


@router.get("/events", response_model=list[StoredEventOut])
def list_events(
    organization_id: str | None = None,
    event_code: str | None = None,
    family: str | None = None,
    correlation_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_ef_read),
    db: Session = Depends(get_db),
) -> list[StoredEventOut]:
    rows = EventFabricService(db).list_events(
        _actor(session),
        organization_id=organization_id,
        event_code=event_code,
        family=family,
        correlation_id=correlation_id,
        limit=limit,
        offset=offset,
    )
    return [StoredEventOut.model_validate(r) for r in rows]


@router.get("/events/{event_id}", response_model=StoredEventOut)
def get_event(
    event_id: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_ef_read),
    db: Session = Depends(get_db),
) -> StoredEventOut:
    row = EventFabricService(db).get_event(_actor(session), event_id, organization_id)
    return StoredEventOut.model_validate(row)


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_ef_read),
    db: Session = Depends(get_db),
) -> list[SubscriptionOut]:
    rows = EventFabricService(db).list_subscriptions(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )
    return [SubscriptionOut.model_validate(r) for r in rows]


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=201)
def create_subscription(
    payload: SubscriptionCreate,
    session: Session_ = Depends(require_ef_manage),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    row = EventFabricService(db).create_subscription(_actor(session), **payload.model_dump())
    return SubscriptionOut.model_validate(row)


@router.get("/dlq", response_model=list[DeadLetterOut])
def list_dlq(
    organization_id: str | None = None,
    status_filter: str | None = Query("open", alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_ef_read),
    db: Session = Depends(get_db),
) -> list[DeadLetterOut]:
    rows = EventFabricService(db).list_dlq(
        _actor(session),
        organization_id=organization_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [DeadLetterOut.model_validate(r) for r in rows]


class DeadLetterCreate(BaseModel):
    organization_id: str | None = None
    store_event_id: str
    subscriber_name: str = Field(min_length=1)
    error_message: str = ""


@router.post("/dlq", response_model=DeadLetterOut, status_code=201)
def create_dlq(
    payload: DeadLetterCreate,
    session: Session_ = Depends(require_ef_manage),
    db: Session = Depends(get_db),
) -> DeadLetterOut:
    row = EventFabricService(db).dead_letter(
        _actor(session),
        store_event_id=payload.store_event_id,
        subscriber_name=payload.subscriber_name,
        error_message=payload.error_message,
        organization_id=payload.organization_id,
    )
    return DeadLetterOut.model_validate(row)


@router.post("/dlq/{dlq_id}/retry", response_model=DeadLetterOut)
def retry_dlq(
    dlq_id: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_ef_manage),
    db: Session = Depends(get_db),
) -> DeadLetterOut:
    row = EventFabricService(db).retry_dlq(_actor(session), dlq_id, organization_id)
    return DeadLetterOut.model_validate(row)


@router.post("/replay", response_model=ReplayOut)
def replay_events(
    payload: ReplayRequest,
    session: Session_ = Depends(require_ef_manage),
    db: Session = Depends(get_db),
) -> ReplayOut:
    return EventFabricService(db).replay(_actor(session), **payload.model_dump())
