from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..database import get_db
from ..security.authorization import has_permissions
from ..security.operators import operator_store
from ..security.runtime_authz import require_allowed
from ..shared import clamp_page
from .schemas import (
    CompanyCreate,
    CompanyOut,
    DepartmentCreate,
    DepartmentOut,
    MembershipCreate,
    MembershipOut,
    OrganizationCreate,
    OrganizationOut,
    SiteCreate,
    SiteOut,
    TeamCreate,
    TeamOut,
    UserCreate,
    UserOut,
)
from .service import OrganizationService

logger = logging.getLogger("mercury.org")
router = APIRouter(prefix="/api/v1", tags=["organizations"])


def _session(request: Request) -> dict[str, datetime | str]:
    from ..main import require_session

    return require_session(request)


def require_org_read(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(db, session, ("org.read",), detail="Insufficient permissions")
    return session


def require_org_manage(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    # Platform privilege must come from the login directory, never membership elevation.
    username = str(session.get("operator", ""))
    record = operator_store.get(username)
    global_role = record["role"] if record else str(session.get("role", ""))
    if not has_permissions(global_role, ("admin.system",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization management required")
    return session


def _svc(db: Session) -> OrganizationService:
    return OrganizationService(db)


def _safe_commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _audit_org(
    db: Session,
    session: dict[str, datetime | str],
    *,
    action: str,
    target_type: str,
    target_id: str,
    details: str = "",
    organization_id: str | None = None,
    site_id: str | None = None,
) -> None:
    try:
        record_audit(
            db,
            action=action,
            actor=str(session["operator"]),
            actor_role=str(session["role"]),
            organization_id=organization_id or str(session["organization_id"]),
            site_id=site_id or str(session["site_id"]),
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
        logger.exception("Failed to record organization audit action=%s target=%s", action, target_id)


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_read),
) -> list[CompanyOut]:
    svc = _svc(db)
    actor = str(session["operator"])
    role = str(session["role"])
    lim, off = clamp_page(limit, offset)
    if not svc.is_platform_admin(actor, role):
        allowed = svc.allowed_organization_ids(actor, role) or set()
        orgs = [o for o in svc.repo.list_organizations(active_only=True) if o.id in allowed]
        company_ids = {o.company_id for o in orgs}
        rows = [c for c in svc.repo.list_companies() if c.id in company_ids]
        return [svc.company_out(c) for c in rows[off : off + lim]]
    return [svc.company_out(c) for c in svc.repo.list_companies(limit=lim, offset=off)]


@router.post("/companies", response_model=CompanyOut, status_code=201)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_manage),
) -> CompanyOut:
    out = _svc(db).create_company(payload)
    _audit_org(db, session, action="org.company.create", target_type="company", target_id=out.id, details=out.code)
    return out


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(
    company_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_read),
) -> list[OrganizationOut]:
    svc = _svc(db)
    rows = svc.repo.list_organizations(company_id=company_id, active_only=True)
    allowed = svc.allowed_organization_ids(str(session["operator"]), str(session["role"]))
    if allowed is not None:
        rows = [r for r in rows if r.id in allowed]
    lim, off = clamp_page(limit, offset)
    rows = rows[off : off + lim]
    return [svc.organization_out(r) for r in rows]


@router.post("/organizations", response_model=OrganizationOut, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_manage),
) -> OrganizationOut:
    out = _svc(db).create_organization(payload)
    _audit_org(
        db,
        session,
        action="org.organization.create",
        target_type="organization",
        target_id=out.organization_id,
        details=out.code,
        organization_id=out.organization_id,
    )
    return out


@router.get("/organizations/{organization_id}", response_model=OrganizationOut)
def get_organization(
    organization_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_read),
) -> OrganizationOut:
    svc = _svc(db)
    svc.assert_org_access(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        organization_id=organization_id,
    )
    return svc.get_organization_out(organization_id)


@router.get("/organizations/{organization_id}/sites", response_model=list[SiteOut])
def list_organization_sites(
    organization_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_read),
) -> list[SiteOut]:
    return _svc(db).sites_for_session(
        str(session["operator"]),
        str(session["role"]),
        organization_id,
        limit=limit,
        offset=offset,
    )


@router.get("/sites", response_model=list[SiteOut])
def list_sites(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_read),
) -> list[SiteOut]:
    svc = _svc(db)
    org_id = organization_id or str(session["organization_id"])
    return svc.sites_for_session(
        str(session["operator"]), str(session["role"]), org_id, limit=limit, offset=offset
    )


@router.post("/sites", response_model=SiteOut, status_code=201)
def create_site(
    payload: SiteCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_manage),
) -> SiteOut:
    out = _svc(db).create_site(payload)
    _audit_org(
        db,
        session,
        action="org.site.create",
        target_type="site",
        target_id=out.site_id,
        details=out.code,
        organization_id=out.organization_id,
        site_id=out.site_id,
    )
    return out


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_read),
) -> list[DepartmentOut]:
    svc = _svc(db)
    org_id = organization_id or str(session["organization_id"])
    svc.assert_org_access(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        organization_id=org_id,
    )
    rows = svc.repo.list_departments(organization_id=org_id, active_only=True, limit=limit, offset=offset)
    return [svc.department_out(r) for r in rows]


@router.post("/departments", response_model=DepartmentOut, status_code=201)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_manage),
) -> DepartmentOut:
    out = _svc(db).create_department(payload)
    _audit_org(
        db,
        session,
        action="org.department.create",
        target_type="department",
        target_id=out.id,
        details=out.code,
        organization_id=out.organization_id,
        site_id=out.site_id or str(session["site_id"]),
    )
    return out


@router.get("/teams", response_model=list[TeamOut])
def list_teams(
    organization_id: str | None = None,
    department_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_read),
) -> list[TeamOut]:
    svc = _svc(db)
    org_id = organization_id or str(session["organization_id"])
    svc.assert_org_access(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        organization_id=org_id,
    )
    rows = svc.repo.list_teams(
        organization_id=org_id, department_id=department_id, active_only=True, limit=limit, offset=offset
    )
    return [svc.team_out(r) for r in rows]


@router.post("/teams", response_model=TeamOut, status_code=201)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_manage),
) -> TeamOut:
    out = _svc(db).create_team(payload)
    _audit_org(
        db,
        session,
        action="org.team.create",
        target_type="team",
        target_id=out.id,
        details=out.code,
        organization_id=out.organization_id,
    )
    return out


@router.get("/org/users", response_model=list[UserOut])
def list_org_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_manage),
) -> list[UserOut]:
    return [_svc(db).user_out(r) for r in _svc(db).repo.list_users(limit=limit, offset=offset)]


@router.post("/org/users", response_model=UserOut, status_code=201)
def create_org_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_manage),
) -> UserOut:
    svc = _svc(db)
    out = svc.create_user(payload)
    try:
        operator_store.register_role(out.username, "Viewer")
    except ValueError as exc:
        logger.exception("operator_store sync failed for %s", out.username)
        raise HTTPException(status_code=500, detail="User directory sync failed") from exc
    _audit_org(db, session, action="org.user.create", target_type="user", target_id=out.username)
    return out


@router.get("/memberships", response_model=list[MembershipOut])
def list_memberships(
    organization_id: str | None = None,
    username: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_read),
) -> list[MembershipOut]:
    svc = _svc(db)
    actor = str(session["operator"])
    role = str(session["role"])
    is_admin = svc.is_platform_admin(actor, role)

    # Non-admins may only read their own memberships (org.manage for directory listing).
    if not is_admin:
        if username and username != actor:
            raise HTTPException(status_code=403, detail="Cannot list other users' memberships")
        username = actor
        if organization_id:
            svc.assert_org_access(username=actor, session_role=role, organization_id=organization_id)
    elif organization_id:
        svc.assert_org_access(username=actor, session_role=role, organization_id=organization_id)

    rows = svc.repo.list_memberships(
        organization_id=organization_id,
        username=username,
        active_only=True,
        with_user=True,
    )
    if not is_admin:
        allowed = svc.allowed_organization_ids(actor, role) or set()
        rows = [m for m in rows if m.organization_id in allowed]

    lim, off = clamp_page(limit, offset)
    rows = rows[off : off + lim]

    return [
        svc.membership_out(row, row.user.username if row.user else "")
        for row in rows
    ]


@router.post("/memberships", response_model=MembershipOut, status_code=201)
def create_membership(
    payload: MembershipCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_manage),
) -> MembershipOut:
    out = _svc(db).create_membership(payload)
    _audit_org(
        db,
        session,
        action="org.membership.create",
        target_type="membership",
        target_id=out.id,
        details=f"{out.username}:{out.organization_id}:{out.role}",
        organization_id=out.organization_id,
        site_id=out.site_id or str(session["site_id"]),
    )
    return out


@router.get("/org/me")
def my_org_profile(
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_org_read),
) -> dict[str, Any]:
    svc = _svc(db)
    actor = str(session["operator"])
    memberships = svc.user_memberships(actor)
    user = svc.repo.get_user_by_username(actor)
    return {
        "username": actor,
        "role": str(session["role"]),
        "organization_id": str(session["organization_id"]),
        "site_id": str(session["site_id"]),
        "user": svc.user_out(user).model_dump() if user else None,
        "memberships": [svc.membership_out(m, actor).model_dump() for m in memberships],
    }
