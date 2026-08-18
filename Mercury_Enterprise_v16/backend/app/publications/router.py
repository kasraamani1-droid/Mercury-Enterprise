from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..database import get_db
from ..security.authorization import has_permissions
from ..security.operators import operator_store
from ..security.runtime_authz import permissions_allowed, require_allowed
from .schemas import (
    AccessClassificationUpdate,
    ComponentPublicationOut,
    LibraryBrowseOut,
    PublicationCreate,
    PublicationOut,
    PublicationTypeOut,
    PublicationUpdate,
    RevisionCreate,
    RevisionOut,
)
from .service import PublicationService

logger = logging.getLogger("mercury.publications")
router = APIRouter(prefix="/api/v1/publications", tags=["publications"])
library_router = APIRouter(prefix="/api/v1/library", tags=["technical-library"])


def _session(request: Request) -> dict[str, datetime | str]:
    from ..main import require_session

    return require_session(request)


def require_publication_read(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(db, session, ("publication.read",), detail="Insufficient permissions")
    return session


def require_publication_manage(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(db, session, ("publication.manage",), detail="Publication management required")
    return session


def require_publication_admin(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    if permissions_allowed(db, session, ("publication.admin",)):
        return session
    username = str(session.get("operator", ""))
    record = operator_store.get(username)
    global_role = record["role"] if record else str(session.get("role", ""))
    if not has_permissions(global_role, ("publication.admin",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Publication admin required")
    return session


def _svc(db: Session) -> PublicationService:
    return PublicationService(db)


def _safe_commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _audit(
    db: Session,
    session: dict[str, datetime | str],
    *,
    action: str,
    target_type: str,
    target_id: str,
    details: str = "",
    organization_id: str | None = None,
) -> None:
    try:
        record_audit(
            db,
            action=action,
            actor=str(session["operator"]),
            actor_role=str(session["role"]),
            organization_id=organization_id or str(session["organization_id"]),
            site_id=str(session["site_id"]),
            target_type=target_type,
            target_id=target_id,
            source="api",
            outcome="success",
            origin="operator",
            details=details,
        )
        _safe_commit(db)
    except Exception:
        db.rollback()
        logger.exception("Failed to record publication audit action=%s target=%s", action, target_id)


@router.get("/types", response_model=list[PublicationTypeOut])
def list_publication_types(
    category: str | None = None,
    db: Session = Depends(get_db),
    _: dict[str, datetime | str] = Depends(require_publication_read),
) -> list[PublicationTypeOut]:
    return _svc(db).list_types(category=category)


@router.get("/by-ata/{ata_chapter_id}", response_model=list[PublicationOut])
def publications_by_ata(
    ata_chapter_id: str,
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_read),
) -> list[PublicationOut]:
    return _svc(db).publications_for_ata(
        ata_chapter_id,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )


@router.get("/by-model/{aircraft_model_id}", response_model=list[PublicationOut])
def publications_by_model(
    aircraft_model_id: str,
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_read),
) -> list[PublicationOut]:
    return _svc(db).publications_for_model(
        aircraft_model_id,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )


@router.get("/by-component/{component_id}", response_model=ComponentPublicationOut)
def publications_by_component(
    component_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_read),
) -> ComponentPublicationOut:
    return _svc(db).publications_for_component(
        component_id, username=str(session["operator"]), session_role=str(session["role"])
    )


@router.get("/by-aircraft/{aircraft_id}", response_model=list[PublicationOut])
def publications_by_aircraft(
    aircraft_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_read),
) -> list[PublicationOut]:
    return _svc(db).publications_for_aircraft(
        aircraft_id, username=str(session["operator"]), session_role=str(session["role"])
    )


@router.get("", response_model=list[PublicationOut])
def list_or_search_publications(
    organization_id: str | None = None,
    publication_code: str | None = None,
    title: str | None = None,
    aircraft_model_id: str | None = None,
    manufacturer_id: str | None = None,
    ata_chapter_id: str | None = None,
    revision: str | None = None,
    q: str | None = None,
    revision_date_from: datetime | None = None,
    revision_date_to: datetime | None = None,
    effective_date_from: datetime | None = None,
    effective_date_to: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_read),
) -> list[PublicationOut]:
    return _svc(db).search(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        publication_code=publication_code,
        title=title,
        aircraft_model_id=aircraft_model_id,
        manufacturer_id=manufacturer_id,
        ata_chapter_id=ata_chapter_id,
        revision_number=revision,
        q=q,
        revision_date_from=revision_date_from,
        revision_date_to=revision_date_to,
        effective_date_from=effective_date_from,
        effective_date_to=effective_date_to,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=PublicationOut, status_code=201)
def create_publication(
    payload: PublicationCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_manage),
) -> PublicationOut:
    out = _svc(db).create_publication(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="publication.create",
        target_type="publication",
        target_id=out.id,
        details=f"code={out.publication_code};number={out.publication_number}",
        organization_id=out.organization_id,
    )
    revisions = _svc(db).list_revisions(
        out.id, username=str(session["operator"]), session_role=str(session["role"])
    )
    for rev in revisions:
        _audit(
            db,
            session,
            action="publication.revision.create",
            target_type="publication_revision",
            target_id=rev.id,
            details=f"publication_id={out.id};status={rev.status}",
            organization_id=out.organization_id,
        )
        if rev.status == "current":
            _audit(
                db,
                session,
                action="publication.revision.activate",
                target_type="publication_revision",
                target_id=rev.id,
                details=f"publication_id={out.id}",
                organization_id=out.organization_id,
            )
    return out


@router.get("/{publication_id}", response_model=PublicationOut)
def get_publication(
    publication_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_read),
) -> PublicationOut:
    return _svc(db).get_publication(
        publication_id, username=str(session["operator"]), session_role=str(session["role"])
    )


@router.patch("/{publication_id}", response_model=PublicationOut)
def update_publication(
    publication_id: str,
    payload: PublicationUpdate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_manage),
) -> PublicationOut:
    out = _svc(db).update_publication(
        publication_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="publication.update",
        target_type="publication",
        target_id=out.id,
        details="metadata_update",
        organization_id=out.organization_id,
    )
    return out


@router.post("/{publication_id}/access-classification", response_model=PublicationOut)
def update_access_classification(
    publication_id: str,
    payload: AccessClassificationUpdate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_admin),
) -> PublicationOut:
    out = _svc(db).set_access_classification(
        publication_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="publication.access_control",
        target_type="publication",
        target_id=out.id,
        details=f"access_classification={out.access_classification}",
        organization_id=out.organization_id,
    )
    return out


@router.post("/{publication_id}/archive", response_model=PublicationOut)
def archive_publication(
    publication_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_admin),
) -> PublicationOut:
    out = _svc(db).archive_publication(
        publication_id, username=str(session["operator"]), session_role=str(session["role"])
    )
    _audit(
        db,
        session,
        action="publication.archive",
        target_type="publication",
        target_id=out.id,
        details="archived",
        organization_id=out.organization_id,
    )
    return out


@router.get("/{publication_id}/revisions", response_model=list[RevisionOut])
def list_revisions(
    publication_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_read),
) -> list[RevisionOut]:
    return _svc(db).list_revisions(
        publication_id, username=str(session["operator"]), session_role=str(session["role"])
    )


@router.post("/{publication_id}/revisions", response_model=RevisionOut, status_code=201)
def create_revision(
    publication_id: str,
    payload: RevisionCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_manage),
) -> RevisionOut:
    if payload.activate:
        # Activation is publication.admin only (same gate as dedicated activate endpoint).
        if not permissions_allowed(db, session, ("publication.admin",)):
            username = str(session.get("operator", ""))
            record = operator_store.get(username)
            global_role = record["role"] if record else str(session.get("role", ""))
            if not has_permissions(global_role, ("publication.admin",)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Activating a revision requires publication.admin",
                )
    out = _svc(db).create_revision(
        publication_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="publication.revision.create",
        target_type="publication_revision",
        target_id=out.id,
        details=f"publication_id={publication_id};revision={out.revision_number};status={out.status}",
        organization_id=out.organization_id,
    )
    if out.status == "current":
        _audit(
            db,
            session,
            action="publication.revision.activate",
            target_type="publication_revision",
            target_id=out.id,
            details=f"publication_id={publication_id}",
            organization_id=out.organization_id,
        )
    return out


@router.post("/{publication_id}/revisions/{revision_id}/activate", response_model=RevisionOut)
def activate_revision(
    publication_id: str,
    revision_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_admin),
) -> RevisionOut:
    out = _svc(db).activate_revision(
        publication_id,
        revision_id,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="publication.revision.activate",
        target_type="publication_revision",
        target_id=out.id,
        details=f"publication_id={publication_id};revision={out.revision_number}",
        organization_id=out.organization_id,
    )
    return out


@router.post("/{publication_id}/ata/{ata_chapter_id}", response_model=PublicationOut)
def link_ata(
    publication_id: str,
    ata_chapter_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_manage),
) -> PublicationOut:
    out = _svc(db).link_ata(
        publication_id,
        ata_chapter_id,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="publication.update",
        target_type="publication",
        target_id=out.id,
        details=f"link_ata={ata_chapter_id}",
        organization_id=out.organization_id,
    )
    return out


@router.post("/{publication_id}/catalog/{catalog_item_id}", response_model=PublicationOut)
def link_catalog(
    publication_id: str,
    catalog_item_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_manage),
) -> PublicationOut:
    out = _svc(db).link_catalog(
        publication_id,
        catalog_item_id,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="publication.update",
        target_type="publication",
        target_id=out.id,
        details=f"link_catalog={catalog_item_id}",
        organization_id=out.organization_id,
    )
    return out


@library_router.get("/browse", response_model=LibraryBrowseOut)
def library_browse(
    organization_id: str | None = None,
    manufacturer_id: str | None = None,
    family_id: str | None = None,
    aircraft_model_id: str | None = None,
    publication_code: str | None = None,
    ata_chapter_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_read),
) -> LibraryBrowseOut:
    return _svc(db).library_browse(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        manufacturer_id=manufacturer_id,
        family_id=family_id,
        aircraft_model_id=aircraft_model_id,
        publication_code=publication_code,
        ata_chapter_id=ata_chapter_id,
    )


@library_router.get("/search", response_model=list[PublicationOut])
def library_search(
    q: str | None = Query(default=None),
    organization_id: str | None = None,
    publication_code: str | None = None,
    title: str | None = None,
    aircraft_model_id: str | None = None,
    manufacturer_id: str | None = None,
    ata_chapter_id: str | None = None,
    revision: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_publication_read),
) -> list[PublicationOut]:
    return _svc(db).search(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        publication_code=publication_code,
        title=title,
        aircraft_model_id=aircraft_model_id,
        manufacturer_id=manufacturer_id,
        ata_chapter_id=ata_chapter_id,
        revision_number=revision,
        q=q,
    )
