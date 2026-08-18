"""Authority portal readiness API — no regulatory approval claimed."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from .schemas import AuthorityOut
from .service import AuthorityService

router = APIRouter(prefix="/api/v1/authority", tags=["authority"])
Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_authority_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("authority.read", "platform.read", "org.read"),
        any_of=True,
        detail="Authority read required",
    )
    return session


@router.get("/bodies", response_model=list[AuthorityOut])
def list_authorities(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_authority_read),
    db: Session = Depends(get_db),
) -> list[AuthorityOut]:
    _ = session
    return [AuthorityOut.model_validate(r) for r in AuthorityService(db).list(limit=limit, offset=offset)]


@router.get("/bodies/{code}", response_model=AuthorityOut)
def get_authority(
    code: str,
    session: Session_ = Depends(require_authority_read),
    db: Session = Depends(get_db),
) -> AuthorityOut:
    _ = session
    return AuthorityOut.model_validate(AuthorityService(db).get(code))
