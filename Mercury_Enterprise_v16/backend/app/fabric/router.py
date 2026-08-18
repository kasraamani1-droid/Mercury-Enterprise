"""Program 11 — Universal Data Fabric HTTP API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from ..shared import ActorContext
from .schemas import (
    AttachmentRefCreate,
    AttachmentRefOut,
    DigitalThreadOut,
    EntityTypeOut,
    EventCreate,
    EventOut,
    FabricOverviewOut,
    FabricSearchHit,
    LegalHoldCreate,
    LegalHoldOut,
    PassportCreate,
    PassportHistoryOut,
    PassportOut,
    RelationshipCreate,
    RelationshipOut,
    RetentionPolicyOut,
    TagCreate,
    TagOut,
)
from .service import FabricService

router = APIRouter(prefix="/api/v1/fabric", tags=["fabric"])
Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_fabric_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("fabric.read", "platform.read", "org.read"),
        any_of=True,
        detail="Fabric read required",
    )
    return session


def require_fabric_manage(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("fabric.manage", "platform.manage"),
        any_of=True,
        detail="Fabric manage required",
    )
    return session


def _svc(db: Session) -> FabricService:
    return FabricService(db)


def _actor(session: Session_) -> ActorContext:
    return ActorContext(
        username=str(session["operator"]),
        role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )


@router.get("/overview", response_model=FabricOverviewOut)
def overview(
    organization_id: str | None = None,
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> FabricOverviewOut:
    return _svc(db).overview(_actor(session), organization_id=organization_id)


@router.get("/entity-types", response_model=list[EntityTypeOut])
def list_entity_types(
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> list[EntityTypeOut]:
    _ = session
    return _svc(db).list_entity_types()


@router.post("/passports", response_model=PassportOut, status_code=201)
def ensure_passport(
    payload: PassportCreate,
    session: Session_ = Depends(require_fabric_manage),
    db: Session = Depends(get_db),
) -> PassportOut:
    return _svc(db).ensure_passport(payload, _actor(session))


@router.get("/passports", response_model=list[PassportOut])
def list_passports(
    organization_id: str | None = None,
    entity_type: str | None = None,
    lifecycle: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> list[PassportOut]:
    return _svc(db).list_passports(
        _actor(session),
        organization_id=organization_id,
        entity_type=entity_type,
        lifecycle=lifecycle,
        limit=limit,
        offset=offset,
    )


@router.get("/passports/{passport_id}", response_model=PassportOut)
def get_passport(
    passport_id: str,
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> PassportOut:
    return _svc(db).get_passport(passport_id, _actor(session))


@router.post("/passports/{passport_id}/lifecycle", response_model=PassportOut)
def update_lifecycle(
    passport_id: str,
    lifecycle: str = Query(..., min_length=1, max_length=40),
    session: Session_ = Depends(require_fabric_manage),
    db: Session = Depends(get_db),
) -> PassportOut:
    return _svc(db).update_lifecycle(passport_id, lifecycle, _actor(session))


@router.get("/passports/{passport_id}/history", response_model=list[PassportHistoryOut])
def passport_history(
    passport_id: str,
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> list[PassportHistoryOut]:
    return _svc(db).list_history(passport_id, _actor(session))


@router.get("/passports/{passport_id}/thread", response_model=DigitalThreadOut)
def digital_thread(
    passport_id: str,
    max_depth: int = Query(4, ge=1, le=8),
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> DigitalThreadOut:
    return _svc(db).digital_thread(passport_id, _actor(session), max_depth=max_depth)


@router.post("/relationships", response_model=RelationshipOut, status_code=201)
def create_relationship(
    payload: RelationshipCreate,
    session: Session_ = Depends(require_fabric_manage),
    db: Session = Depends(get_db),
) -> RelationshipOut:
    return _svc(db).link(payload, _actor(session))


@router.get("/relationships", response_model=list[RelationshipOut])
def list_relationships(
    organization_id: str | None = None,
    passport_id: str | None = None,
    relationship_type: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> list[RelationshipOut]:
    return _svc(db).list_relationships(
        _actor(session),
        organization_id=organization_id,
        passport_id=passport_id,
        relationship_type=relationship_type,
        limit=limit,
        offset=offset,
    )


@router.delete("/relationships/{relationship_id}", response_model=RelationshipOut)
def delete_relationship(
    relationship_id: str,
    session: Session_ = Depends(require_fabric_manage),
    db: Session = Depends(get_db),
) -> RelationshipOut:
    return _svc(db).unlink(relationship_id, _actor(session))


@router.post("/events", response_model=EventOut, status_code=201)
def emit_event(
    payload: EventCreate,
    session: Session_ = Depends(require_fabric_manage),
    db: Session = Depends(get_db),
) -> EventOut:
    return _svc(db).emit_event(payload, _actor(session))


@router.get("/events", response_model=list[EventOut])
def list_events(
    organization_id: str | None = None,
    passport_id: str | None = None,
    event_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> list[EventOut]:
    return _svc(db).list_events(
        _actor(session),
        organization_id=organization_id,
        passport_id=passport_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )


@router.post("/tags", response_model=TagOut, status_code=201)
def add_tag(
    payload: TagCreate,
    session: Session_ = Depends(require_fabric_manage),
    db: Session = Depends(get_db),
) -> TagOut:
    return _svc(db).add_tag(payload, _actor(session))


@router.get("/passports/{passport_id}/tags", response_model=list[TagOut])
def list_tags(
    passport_id: str,
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> list[TagOut]:
    return _svc(db).list_tags(passport_id, _actor(session))


@router.post("/attachments", response_model=AttachmentRefOut, status_code=201)
def add_attachment(
    payload: AttachmentRefCreate,
    session: Session_ = Depends(require_fabric_manage),
    db: Session = Depends(get_db),
) -> AttachmentRefOut:
    return _svc(db).add_attachment(payload, _actor(session))


@router.get("/passports/{passport_id}/attachments", response_model=list[AttachmentRefOut])
def list_attachments(
    passport_id: str,
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> list[AttachmentRefOut]:
    return _svc(db).list_attachments(passport_id, _actor(session))


@router.get("/search", response_model=list[FabricSearchHit])
def search(
    q: str = Query(..., min_length=1),
    organization_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> list[FabricSearchHit]:
    return _svc(db).search(_actor(session), query=q, organization_id=organization_id, limit=limit)


@router.get("/governance/retention", response_model=list[RetentionPolicyOut])
def list_retention(
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> list[RetentionPolicyOut]:
    return _svc(db).list_retention_policies(_actor(session))


@router.get("/governance/legal-holds", response_model=list[LegalHoldOut])
def list_holds(
    session: Session_ = Depends(require_fabric_read),
    db: Session = Depends(get_db),
) -> list[LegalHoldOut]:
    return _svc(db).list_legal_holds(_actor(session))


@router.post("/governance/legal-holds", response_model=LegalHoldOut, status_code=201)
def place_hold(
    payload: LegalHoldCreate,
    session: Session_ = Depends(require_fabric_manage),
    db: Session = Depends(get_db),
) -> LegalHoldOut:
    return _svc(db).place_legal_hold(payload, _actor(session))


@router.post("/governance/legal-holds/{hold_id}/release", response_model=LegalHoldOut)
def release_hold(
    hold_id: str,
    session: Session_ = Depends(require_fabric_manage),
    db: Session = Depends(get_db),
) -> LegalHoldOut:
    return _svc(db).release_legal_hold(hold_id, _actor(session))
