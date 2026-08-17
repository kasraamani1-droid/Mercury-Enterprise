"""Aviation Digital Ecosystem HTTP API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from ..shared import ActorContext
from .schemas import (
    CapabilityOut,
    EcosystemDetailOut,
    EcosystemOut,
    EcosystemOverviewOut,
    EnrollmentCreate,
    EnrollmentOut,
)
from .service import EcosystemService

router = APIRouter(prefix="/api/v1/ecosystem", tags=["ecosystem"])
Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_ecosystem_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("ecosystem.read", "platform.read", "org.read"),
        any_of=True,
        detail="Ecosystem read required",
    )
    return session


def require_ecosystem_manage(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("ecosystem.manage", "platform.manage"),
        any_of=True,
        detail="Ecosystem manage required",
    )
    return session


def _actor(session: Session_) -> ActorContext:
    return ActorContext(
        username=str(session["operator"]),
        role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )


@router.get("/overview", response_model=EcosystemOverviewOut)
def overview(
    organization_id: str | None = None,
    session: Session_ = Depends(require_ecosystem_read),
    db: Session = Depends(get_db),
) -> EcosystemOverviewOut:
    return EcosystemService(db).overview(_actor(session), organization_id=organization_id)


@router.get("/definitions", response_model=list[EcosystemOut])
def list_ecosystems(
    session: Session_ = Depends(require_ecosystem_read),
    db: Session = Depends(get_db),
) -> list[EcosystemOut]:
    _ = session
    return EcosystemService(db).list_ecosystems()


@router.get("/definitions/{code}", response_model=EcosystemDetailOut)
def get_ecosystem(
    code: str,
    session: Session_ = Depends(require_ecosystem_read),
    db: Session = Depends(get_db),
) -> EcosystemDetailOut:
    _ = session
    return EcosystemService(db).get_ecosystem(code)


@router.get("/capabilities", response_model=list[CapabilityOut])
def list_capabilities(
    ecosystem_code: str | None = None,
    session: Session_ = Depends(require_ecosystem_read),
    db: Session = Depends(get_db),
) -> list[CapabilityOut]:
    _ = session
    return EcosystemService(db).list_capabilities(ecosystem_code)


@router.post("/enrollments", response_model=EnrollmentOut, status_code=201)
def enroll(
    payload: EnrollmentCreate,
    session: Session_ = Depends(require_ecosystem_manage),
    db: Session = Depends(get_db),
) -> EnrollmentOut:
    return EcosystemService(db).enroll(payload, _actor(session))


@router.get("/enrollments", response_model=list[EnrollmentOut])
def list_enrollments(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_ecosystem_read),
    db: Session = Depends(get_db),
) -> list[EnrollmentOut]:
    return EcosystemService(db).list_enrollments(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )
