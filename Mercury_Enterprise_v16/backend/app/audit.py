from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .core.config import settings
from .models import AuditEvent


PROVENANCE_SIMULATED = "simulated"
PROVENANCE_OPERATOR = "operator_entered"
PROVENANCE_SYSTEM = "system_generated"
ORIGIN_OPERATOR = "operator"
ORIGIN_SYSTEM = "system"
ORIGIN_SIMULATED = "simulated"
ALLOWED_PROVENANCE = {
    PROVENANCE_SIMULATED,
    PROVENANCE_OPERATOR,
    PROVENANCE_SYSTEM,
}


def normalize_provenance(value: str | None, *, default: str = PROVENANCE_OPERATOR) -> str:
    if value is None or not str(value).strip():
        return default
    normalized = str(value).strip()
    if normalized not in ALLOWED_PROVENANCE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provenance")
    return normalized


def record_audit(
    db: Session,
    *,
    action: str,
    actor: str,
    organization_id: str,
    site_id: str,
    actor_role: str = "",
    target_type: str | None = None,
    target_id: str | None = None,
    source: str = "api",
    outcome: str = "success",
    origin: str = ORIGIN_OPERATOR,
    details: str = "",
) -> AuditEvent:
    event = AuditEvent(
        action=action,
        actor=actor,
        actor_role=actor_role or "",
        organization_id=organization_id,
        site_id=site_id,
        target_type=target_type,
        target_id=target_id,
        source=source,
        outcome=outcome,
        origin=origin,
        details=details or "",
    )
    db.add(event)
    return event


# Canonical audit action names used across Mercury observability.
ACTION_LOGIN = "auth.login"
ACTION_LOGOUT = "auth.logout"
ACTION_LOGIN_FAILURE = "security.login_failure"
ACTION_USER_CREATE = "user.create"
ACTION_PASSWORD_CHANGE = "user.password_change"
ACTION_ROLE_CHANGE = "user.role_change"
ACTION_CONFIG_CHANGE = "config.change"
ACTION_API_ACCESS = "api.access"
ACTION_SECURITY_EVENT = "security.event"
ACTION_AUTHZ_DENIED = "security.authz_denied"
ACTION_OIDC_LOGIN = "auth.oidc_login"


def list_audit_events(
    db: Session,
    *,
    organization_id: str,
    site_id: str,
    action: str | None = None,
    target_id: str | None = None,
    limit: int = 100,
    retention_days: int | None = None,
) -> list[AuditEvent]:
    clamped_limit = max(1, min(int(limit), 500))
    days = settings.audit_retention_days if retention_days is None else retention_days
    cutoff = datetime.utcnow() - timedelta(days=max(1, int(days)))

    stmt = (
        select(AuditEvent)
        .where(AuditEvent.organization_id == organization_id)
        .where(AuditEvent.site_id == site_id)
        .where(AuditEvent.occurred_at >= cutoff)
    )
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if target_id:
        stmt = stmt.where(AuditEvent.target_id == target_id)
    stmt = stmt.order_by(AuditEvent.occurred_at.desc()).limit(clamped_limit)
    return list(db.scalars(stmt).all())


def list_audit_events_admin(
    db: Session,
    *,
    action: str | None = None,
    actor: str | None = None,
    limit: int = 100,
    retention_days: int | None = None,
) -> list[AuditEvent]:
    """Administrator cross-site audit listing."""
    clamped_limit = max(1, min(int(limit), 500))
    days = settings.audit_retention_days if retention_days is None else retention_days
    cutoff = datetime.utcnow() - timedelta(days=max(1, int(days)))
    stmt = select(AuditEvent).where(AuditEvent.occurred_at >= cutoff)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if actor:
        stmt = stmt.where(AuditEvent.actor == actor)
    stmt = stmt.order_by(AuditEvent.occurred_at.desc()).limit(clamped_limit)
    return list(db.scalars(stmt).all())
