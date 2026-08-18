"""Permission Service — enterprise RBAC over session roles + platform extensions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..security.authorization import has_permissions
from .models import PlatformCustomRole, PlatformTemporaryAccess


class PermissionService:
    """Central permission evaluation.

    Domains must not invent module-specific RBAC engines. They call this service
    (or has_permissions for simple session-role checks). Temporary access and
    custom role grants are merged here when present.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def session_allows(self, role: str | None, required: tuple[str, ...]) -> bool:
        return has_permissions(role, required)

    def effective_permissions(
        self, *, username: str, role: str, organization_id: str
    ) -> set[str]:
        """Union of session-role permissions, active temporary grants, and assigned custom roles."""
        granted: set[str] = set()
        # Session role — Administrator short-circuits via has_permissions("*")
        if has_permissions(role, ("*",)):
            return {"*"}
        # Collect by probing known permission prefixes from role matrix is expensive;
        # temporary + custom roles are additive overlays for non-admin users.
        now = datetime.utcnow()
        temps = self.db.scalars(
            select(PlatformTemporaryAccess).where(
                PlatformTemporaryAccess.organization_id == organization_id,
                PlatformTemporaryAccess.username == username,
                PlatformTemporaryAccess.status == "active",
                PlatformTemporaryAccess.starts_at <= now,
                PlatformTemporaryAccess.ends_at > now,
            )
        ).all()
        for row in temps:
            granted.update(p.strip() for p in (row.permissions or "").split(",") if p.strip())

        # Custom roles currently selected by code match on username via details is not enough —
        # use active custom roles that were created for org as templates available for grant;
        # assignment is via temporary access or future role_assignment table.
        # Include any custom role whose code is present in a temp grant of form "role:<code>"
        role_codes = {p[5:] for p in granted if p.startswith("role:")}
        if role_codes:
            customs = self.db.scalars(
                select(PlatformCustomRole).where(
                    PlatformCustomRole.organization_id == organization_id,
                    PlatformCustomRole.deleted_at.is_(None),
                    PlatformCustomRole.status == "active",
                    PlatformCustomRole.code.in_(role_codes),
                )
            ).all()
            for custom in customs:
                granted.update(p.strip() for p in (custom.permissions or "").split(",") if p.strip())

        return granted

    def allows(
        self,
        *,
        username: str,
        role: str,
        organization_id: str,
        required: tuple[str, ...],
    ) -> bool:
        if has_permissions(role, required):
            return True
        extras = self.effective_permissions(
            username=username, role=role, organization_id=organization_id
        )
        if "*" in extras:
            return True
        return all(perm in extras for perm in required)
