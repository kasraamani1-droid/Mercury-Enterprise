"""OEM manufacturer portal readiness API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from .schemas import ManufacturerOut
from .service import OemService

router = APIRouter(prefix="/api/v1/oem", tags=["oem"])
Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_oem_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("oem.read", "platform.read", "org.read"),
        any_of=True,
        detail="OEM read required",
    )
    return session


@router.get("/manufacturers", response_model=list[ManufacturerOut])
def list_manufacturers(
    category: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_oem_read),
    db: Session = Depends(get_db),
) -> list[ManufacturerOut]:
    _ = session
    rows = OemService(db).list(category=category, limit=limit, offset=offset)
    return [ManufacturerOut.model_validate(r) for r in rows]


@router.get("/manufacturers/{code}", response_model=ManufacturerOut)
def get_manufacturer(
    code: str,
    session: Session_ = Depends(require_oem_read),
    db: Session = Depends(get_db),
) -> ManufacturerOut:
    _ = session
    return ManufacturerOut.model_validate(OemService(db).get(code))
