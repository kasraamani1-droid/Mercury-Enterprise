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
        "approval.request",
        "alerts.ack",
    },
    Role.REVIEWER: {
        "approval.review",
        "alerts.ack",
    },
    Role.VIEWER: set(),
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
