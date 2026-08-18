from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..audit import (
    ACTION_CONFIG_CHANGE,
    ACTION_PASSWORD_CHANGE,
    ACTION_ROLE_CHANGE,
    ACTION_USER_CREATE,
    list_audit_events_admin,
    record_audit,
)
from ..connectors.manager import connector_manager
from ..core import metrics as metrics_mod
from ..core.config import settings
from ..core.health import build_health_payload
from ..database import get_db
from ..security.authorization import Role, has_permissions
from ..security.operators import operator_store

router = APIRouter(tags=["admin"])


class UserCreateRequest(BaseModel):
    operator: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=12, max_length=200)
    role: str = Role.VIEWER.value


class PasswordChangeRequest(BaseModel):
    operator: str
    password: str = Field(min_length=12, max_length=200)


class RoleChangeRequest(BaseModel):
    operator: str
    role: str


class ConfigChangeRequest(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(max_length=500)
    reason: str = ""


def _require_admin(session: dict[str, datetime | str]) -> dict[str, datetime | str]:
    role = str(session.get("role", ""))
    if not has_permissions(role, ("admin.system",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator required")
    return session


def get_admin_session(request: Request) -> dict[str, datetime | str]:
    from ..main import require_session

    return _require_admin(require_session(request))


def _safe_commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _apply_runtime_config(key: str, value: str) -> None:
    truthy = value.strip().lower() in {"1", "true", "yes", "on"}
    if key == "MERCURY_AUDIT_API_ACCESS":
        object.__setattr__(settings, "audit_api_access", truthy)
    elif key == "MERCURY_METRICS_ENABLED":
        object.__setattr__(settings, "metrics_enabled", truthy)
    elif key == "MERCURY_LOG_JSON":
        object.__setattr__(settings, "log_json", truthy)
    elif key == "LOG_LEVEL":
        level_name = value.strip().upper() or "INFO"
        logging.getLogger().setLevel(getattr(logging, level_name, logging.INFO))
    elif key == "MERCURY_RATE_LIMIT_LOGIN_PER_MINUTE":
        object.__setattr__(settings, "rate_limit_login_per_minute", max(0, int(value)))
    elif key == "MERCURY_RATE_LIMIT_API_PER_MINUTE":
        object.__setattr__(settings, "rate_limit_api_per_minute", max(0, int(value)))


@router.get("/admin/system")
def admin_system(session: dict[str, datetime | str] = Depends(get_admin_session)) -> dict[str, Any]:
    from ..security.sessions import session_store

    metrics_mod.set_active_users(session_store.count())
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "api_version": settings.version,
        "build_version": settings.build_version,
        "uptime_seconds": round(__import__("time").time() - metrics_mod.STARTED_AT, 3),
        "metrics_enabled": settings.metrics_enabled,
        "log_json": settings.log_json,
        "audit_retention_days": settings.audit_retention_days,
        "redis_configured": bool((settings.redis_url or "").strip()),
        "session_backend": session_store.backend_name,
        "active_users": session_store.count(),
        "operators": operator_store.list_operators(),
        "requested_by": str(session["operator"]),
    }


@router.get("/admin/health")
def admin_health(
    db: Session = Depends(get_db),
    _: dict[str, datetime | str] = Depends(get_admin_session),
) -> dict[str, Any]:
    return build_health_payload(db, connector_manager)


@router.get("/admin/metrics")
def admin_metrics(_: dict[str, datetime | str] = Depends(get_admin_session)) -> dict[str, Any]:
    from ..security.sessions import session_store

    metrics_mod.set_active_users(session_store.count())
    return metrics_mod.metrics_snapshot()


@router.get("/admin/audit")
def admin_audit(
    action: str | None = None,
    actor: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict[str, datetime | str] = Depends(get_admin_session),
) -> list[dict[str, Any]]:
    events = list_audit_events_admin(db, action=action, actor=actor, limit=limit)
    return [
        {
            "id": event.id,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            "action": event.action,
            "actor": event.actor,
            "actor_role": event.actor_role,
            "organization_id": event.organization_id,
            "site_id": event.site_id,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "source": event.source,
            "outcome": event.outcome,
            "origin": event.origin,
            "details": event.details,
        }
        for event in events
    ]


@router.post("/admin/users")
def admin_create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(get_admin_session),
) -> dict[str, Any]:
    try:
        Role(payload.role)
        created = operator_store.create(payload.operator, payload.password, payload.role, db=db)
    except ValueError as exc:
        code = str(exc)
        if code == "operator_exists":
            raise HTTPException(status_code=409, detail="Operator already exists") from exc
        if code in {"invalid_operator_name", "weak_password", "forbidden_password"}:
            raise HTTPException(status_code=400, detail="Invalid operator payload") from exc
        raise HTTPException(status_code=400, detail="Invalid operator payload") from exc
    record_audit(
        db,
        action=ACTION_USER_CREATE,
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="user",
        target_id=created["operator"],
        source="admin",
        outcome="success",
        details=f"role={payload.role}",
    )
    _safe_commit(db)
    return created


@router.post("/admin/users/password")
def admin_change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(get_admin_session),
) -> dict[str, Any]:
    try:
        updated = operator_store.set_password(payload.operator, payload.password, db=db)
    except ValueError as exc:
        code = str(exc)
        if code == "operator_not_found":
            raise HTTPException(status_code=404, detail="Operator not found") from exc
        raise HTTPException(status_code=400, detail="Invalid password") from exc
    record_audit(
        db,
        action=ACTION_PASSWORD_CHANGE,
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="user",
        target_id=payload.operator,
        source="admin",
        outcome="success",
        details="",
    )
    _safe_commit(db)
    return {"updated": True, **updated}


@router.post("/admin/users/role")
def admin_change_role(
    payload: RoleChangeRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(get_admin_session),
) -> dict[str, Any]:
    try:
        Role(payload.role)
        updated = operator_store.set_role(payload.operator, payload.role, db=db)
    except ValueError as exc:
        code = str(exc)
        if code == "operator_not_found":
            raise HTTPException(status_code=404, detail="Operator not found") from exc
        if code == "last_admin":
            raise HTTPException(status_code=409, detail="Cannot demote the last Administrator") from exc
        raise HTTPException(status_code=400, detail="Invalid role") from exc
    record_audit(
        db,
        action=ACTION_ROLE_CHANGE,
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="user",
        target_id=payload.operator,
        source="admin",
        outcome="success",
        details=f"role={payload.role}",
    )
    _safe_commit(db)
    return updated


@router.post("/admin/config")
def admin_config_change(
    payload: ConfigChangeRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(get_admin_session),
) -> dict[str, Any]:
    """Record a configuration change audit event for allow-listed operational keys."""
    allowed = {
        "MERCURY_LOG_JSON",
        "LOG_LEVEL",
        "MERCURY_AUDIT_API_ACCESS",
        "MERCURY_METRICS_ENABLED",
        "MERCURY_RATE_LIMIT_LOGIN_PER_MINUTE",
        "MERCURY_RATE_LIMIT_API_PER_MINUTE",
    }
    if payload.key not in allowed:
        raise HTTPException(status_code=400, detail="Configuration key not allow-listed")
    try:
        _apply_runtime_config(payload.key, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid configuration value") from exc
    os.environ[payload.key] = payload.value
    record_audit(
        db,
        action=ACTION_CONFIG_CHANGE,
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="config",
        target_id=payload.key,
        source="admin",
        outcome="success",
        details=(payload.reason or "")[:500],
    )
    _safe_commit(db)
    return {"updated": True, "key": payload.key}
