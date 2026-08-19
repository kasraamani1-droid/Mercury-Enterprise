"""Runtime authorization — session role + temporary access + custom roles.

Routers must call ``permissions_allowed`` (or ``permissions_allowed_any``) instead of
raw ``has_permissions`` so Platform temporary grants and custom roles take effect.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session


def permissions_allowed(
    db: Session,
    session: dict[str, Any],
    required: tuple[str, ...],
) -> bool:
    """True when session role or org-scoped temp/custom grants satisfy ALL required perms."""
    from ..platform.permission_service import PermissionService

    return PermissionService(db).allows(
        username=str(session.get("operator") or ""),
        role=str(session.get("role") or ""),
        organization_id=str(session.get("organization_id") or ""),
        required=required,
    )


def permissions_allowed_any(
    db: Session,
    session: dict[str, Any],
    candidates: tuple[str, ...],
) -> bool:
    """True when ANY candidate permission is granted (role or temp/custom overlay)."""
    return any(permissions_allowed(db, session, (perm,)) for perm in candidates)


def require_allowed(
    db: Session,
    session: dict[str, Any],
    required: tuple[str, ...],
    *,
    detail: str = "Insufficient permissions",
    any_of: bool = False,
) -> None:
    ok = (
        permissions_allowed_any(db, session, required)
        if any_of
        else permissions_allowed(db, session, required)
    )
    if not ok:
        try:
            from ..audit import ACTION_AUTHZ_DENIED, record_audit
            from ..database import SessionLocal

            audit_db = SessionLocal()
            try:
                record_audit(
                    audit_db,
                    action=ACTION_AUTHZ_DENIED,
                    actor=str(session.get("operator") or ""),
                    actor_role=str(session.get("role") or ""),
                    organization_id=str(session.get("organization_id") or ""),
                    site_id=str(session.get("site_id") or ""),
                    target_type="permission",
                    target_id=",".join(required)[:120],
                    source="api",
                    outcome="failure",
                    origin="system",
                    details=detail,
                )
                audit_db.commit()
            finally:
                audit_db.close()
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
