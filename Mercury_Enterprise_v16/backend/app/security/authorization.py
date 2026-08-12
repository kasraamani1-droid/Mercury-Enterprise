from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMINISTRATOR = "Administrator"
    OPERATOR = "Operator"
    REVIEWER = "Reviewer"
    VIEWER = "Viewer"


PERMISSIONS_BY_ROLE: dict[Role, set[str]] = {
    Role.ADMINISTRATOR: {"*"},
    Role.OPERATOR: {
        "incident.create",
        "incident.update",
        "incident.event",
        "incident.evidence",
        "incident.read",
        "approval.request",
        "alerts.ack",
        "alerts.read",
        "reports.read",
        "connectors.read",
        "connectors.manage",
        "decisions.read",
        "decisions.review",
        "dashboard.read",
        "platform.read",
        "ops.read",
        "ops.coordinate",
        "org.read",
    },
    Role.REVIEWER: {
        "approval.review",
        "alerts.ack",
        "alerts.read",
        "audit.read",
        "reports.read",
        "connectors.read",
        "decisions.read",
        "decisions.review",
        "incident.read",
        "dashboard.read",
        "platform.read",
        "org.read",
    },
    Role.VIEWER: {
        "reports.read",
        "connectors.read",
        "decisions.read",
        "incident.read",
        "alerts.read",
        "dashboard.read",
        "platform.read",
        "org.read",
    },
}


def parse_role(value: str | None) -> Role:
    if not value:
        return Role.VIEWER
    normalized = value.strip().lower()
    for role in Role:
        if role.value.lower() == normalized:
            return role
    return Role.VIEWER


def has_permissions(role_value: str | None, required: tuple[str, ...]) -> bool:
    role = parse_role(role_value)
    granted = PERMISSIONS_BY_ROLE.get(role, set())
    if "*" in granted:
        return True
    return all(permission in granted for permission in required)
