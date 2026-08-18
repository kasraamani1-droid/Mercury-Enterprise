"""Audit Engine — single fail-closed entry point for every Mercury mutation."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..shared import ActorContext

logger = logging.getLogger("mercury.audit_engine")


@dataclass(frozen=True)
class AuditAction:
    """Canonical action catalogue (extend; do not fork)."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"
    RELEASE = "release"
    SIGN = "sign"
    LOGIN = "login"
    PERMISSION_CHANGE = "permission_change"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    TRANSITION = "transition"


class AuditEngine:
    """Wraps record_audit. Critical mutations must use require() (fail-closed)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        actor: ActorContext | None,
        *,
        action: str,
        target_type: str,
        target_id: str,
        organization_id: str | None = None,
        details: str = "",
        outcome: str = "success",
    ) -> None:
        if actor is None:
            return
        record_audit(
            self.db,
            action=action,
            actor=actor.username,
            actor_role=actor.role,
            organization_id=organization_id or actor.organization_id,
            site_id=actor.site_id,
            target_type=target_type,
            target_id=target_id,
            source="api",
            outcome=outcome,
            origin="operator",
            details=details,
        )

    def require(
        self,
        actor: ActorContext | None,
        *,
        action: str,
        target_type: str,
        target_id: str,
        organization_id: str | None = None,
        details: str = "",
        flush: bool = True,
    ) -> None:
        """Fail-closed audit. Rolls back caller transaction on failure."""
        if actor is None:
            return
        try:
            self.record(
                actor,
                action=action,
                target_type=target_type,
                target_id=target_id,
                organization_id=organization_id,
                details=details,
            )
            if flush:
                self.db.flush()
        except Exception as exc:
            self.db.rollback()
            logger.exception("audit engine failed action=%s target=%s", action, target_id)
            raise HTTPException(
                status_code=500, detail="Audit trail write failed; operation rolled back"
            ) from exc
