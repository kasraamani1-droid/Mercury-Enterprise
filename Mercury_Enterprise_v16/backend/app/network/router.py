"""Program 14 — Mercury Aviation Network HTTP API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from ..shared import ActorContext
from .schemas import (
    CollaborationCreate,
    CollaborationOut,
    DirectorySearchResponse,
    DocumentShareCreate,
    DocumentShareOut,
    EventCreate,
    EventOut,
    MessageCreate,
    MessageOut,
    NetworkOverviewOut,
    OrgProfileCreate,
    OrgProfileOut,
    PartnershipApprove,
    PartnershipCreate,
    PartnershipOut,
    ProfessionalCreate,
    ProfessionalOut,
    ThreadCreate,
    ThreadOut,
)
from .service import NetworkService

router = APIRouter(prefix="/api/v1/network", tags=["network"])
Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_network_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("network.read", "platform.read", "org.read"),
        any_of=True,
        detail="Network read required",
    )
    return session


def require_network_manage(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("network.manage", "platform.manage"),
        any_of=True,
        detail="Network manage required",
    )
    return session


def _actor(session: Session_) -> ActorContext:
    return ActorContext(
        username=str(session["operator"]),
        role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )


@router.get("/overview", response_model=NetworkOverviewOut)
def overview(
    organization_id: str | None = None,
    session: Session_ = Depends(require_network_read),
    db: Session = Depends(get_db),
) -> NetworkOverviewOut:
    return NetworkService(db).overview(_actor(session), organization_id)


@router.get("/directory/search", response_model=DirectorySearchResponse)
def directory_search(
    q: str = "",
    entity_type: str | None = None,
    organization_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_network_read),
    db: Session = Depends(get_db),
) -> DirectorySearchResponse:
    return NetworkService(db).search_directory(
        _actor(session),
        q=q,
        entity_type=entity_type,
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )


@router.get("/org-profiles", response_model=list[OrgProfileOut])
def list_org_profiles(
    organization_id: str | None = None,
    org_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_network_read),
    db: Session = Depends(get_db),
) -> list[OrgProfileOut]:
    rows = NetworkService(db).list_org_profiles(
        _actor(session),
        organization_id=organization_id,
        org_type=org_type,
        limit=limit,
        offset=offset,
    )
    return [OrgProfileOut.model_validate(r) for r in rows]


@router.post("/org-profiles", response_model=OrgProfileOut, status_code=201)
def create_org_profile(
    payload: OrgProfileCreate,
    session: Session_ = Depends(require_network_manage),
    db: Session = Depends(get_db),
) -> OrgProfileOut:
    row = NetworkService(db).create_org_profile(_actor(session), **payload.model_dump())
    return OrgProfileOut.model_validate(row)


@router.get("/professionals", response_model=list[ProfessionalOut])
def list_professionals(
    organization_id: str | None = None,
    professional_role: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_network_read),
    db: Session = Depends(get_db),
) -> list[ProfessionalOut]:
    rows = NetworkService(db).list_professionals(
        _actor(session),
        organization_id=organization_id,
        professional_role=professional_role,
        limit=limit,
        offset=offset,
    )
    return [ProfessionalOut.model_validate(r) for r in rows]


@router.post("/professionals", response_model=ProfessionalOut, status_code=201)
def create_professional(
    payload: ProfessionalCreate,
    session: Session_ = Depends(require_network_manage),
    db: Session = Depends(get_db),
) -> ProfessionalOut:
    row = NetworkService(db).create_professional(_actor(session), **payload.model_dump())
    return ProfessionalOut.model_validate(row)


@router.get("/partnerships", response_model=list[PartnershipOut])
def list_partnerships(
    organization_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_network_read),
    db: Session = Depends(get_db),
) -> list[PartnershipOut]:
    rows = NetworkService(db).list_partnerships(
        _actor(session),
        organization_id=organization_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [PartnershipOut.model_validate(r) for r in rows]


@router.post("/partnerships", response_model=PartnershipOut, status_code=201)
def create_partnership(
    payload: PartnershipCreate,
    session: Session_ = Depends(require_network_manage),
    db: Session = Depends(get_db),
) -> PartnershipOut:
    row = NetworkService(db).create_partnership(_actor(session), **payload.model_dump())
    return PartnershipOut.model_validate(row)


@router.post("/partnerships/{partnership_id}/approve", response_model=PartnershipOut)
def approve_partnership(
    partnership_id: str,
    payload: PartnershipApprove | None = None,
    session: Session_ = Depends(require_network_manage),
    db: Session = Depends(get_db),
) -> PartnershipOut:
    org_id = payload.organization_id if payload else None
    row = NetworkService(db).approve_partnership(_actor(session), partnership_id, org_id)
    return PartnershipOut.model_validate(row)


@router.get("/collaborations", response_model=list[CollaborationOut])
def list_collaborations(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_network_read),
    db: Session = Depends(get_db),
) -> list[CollaborationOut]:
    rows = NetworkService(db).list_collaborations(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )
    return [CollaborationOut.model_validate(r) for r in rows]


@router.post("/collaborations", response_model=CollaborationOut, status_code=201)
def create_collaboration(
    payload: CollaborationCreate,
    session: Session_ = Depends(require_network_manage),
    db: Session = Depends(get_db),
) -> CollaborationOut:
    row = NetworkService(db).create_collaboration(_actor(session), **payload.model_dump())
    return CollaborationOut.model_validate(row)


@router.get("/document-shares", response_model=list[DocumentShareOut])
def list_document_shares(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_network_read),
    db: Session = Depends(get_db),
) -> list[DocumentShareOut]:
    rows = NetworkService(db).list_document_shares(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )
    return [DocumentShareOut.model_validate(r) for r in rows]


@router.post("/document-shares", response_model=DocumentShareOut, status_code=201)
def create_document_share(
    payload: DocumentShareCreate,
    session: Session_ = Depends(require_network_manage),
    db: Session = Depends(get_db),
) -> DocumentShareOut:
    row = NetworkService(db).create_document_share(_actor(session), **payload.model_dump())
    return DocumentShareOut.model_validate(row)


@router.get("/threads", response_model=list[ThreadOut])
def list_threads(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_network_read),
    db: Session = Depends(get_db),
) -> list[ThreadOut]:
    rows = NetworkService(db).list_threads(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )
    return [ThreadOut.model_validate(r) for r in rows]


@router.post("/threads", response_model=ThreadOut, status_code=201)
def create_thread(
    payload: ThreadCreate,
    session: Session_ = Depends(require_network_manage),
    db: Session = Depends(get_db),
) -> ThreadOut:
    row = NetworkService(db).create_thread(_actor(session), **payload.model_dump())
    return ThreadOut.model_validate(row)


@router.get("/threads/{thread_id}/messages", response_model=list[MessageOut])
def list_messages(
    thread_id: str,
    organization_id: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_network_read),
    db: Session = Depends(get_db),
) -> list[MessageOut]:
    rows = NetworkService(db).list_messages(
        _actor(session),
        thread_id,
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )
    return [MessageOut.model_validate(r) for r in rows]


@router.post("/messages", response_model=MessageOut, status_code=201)
def post_message(
    payload: MessageCreate,
    session: Session_ = Depends(require_network_manage),
    db: Session = Depends(get_db),
) -> MessageOut:
    row = NetworkService(db).post_message(_actor(session), **payload.model_dump())
    return MessageOut.model_validate(row)


@router.get("/events", response_model=list[EventOut])
def list_events(
    organization_id: str | None = None,
    event_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_network_read),
    db: Session = Depends(get_db),
) -> list[EventOut]:
    rows = NetworkService(db).list_events(
        _actor(session),
        organization_id=organization_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    return [EventOut.model_validate(r) for r in rows]


@router.post("/events", response_model=EventOut, status_code=201)
def create_event(
    payload: EventCreate,
    session: Session_ = Depends(require_network_manage),
    db: Session = Depends(get_db),
) -> EventOut:
    row = NetworkService(db).create_event(_actor(session), **payload.model_dump())
    return EventOut.model_validate(row)
