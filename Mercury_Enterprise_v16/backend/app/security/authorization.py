from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMINISTRATOR = "Administrator"
    OPERATOR = "Operator"
    REVIEWER = "Reviewer"
    VIEWER = "Viewer"


# Aviation personas map onto session roles + fine-grained permissions (see docs/RBAC.md).
AVIATION_PERSONAS = (
    "technician",
    "store",
    "planner",
    "inspector",
    "aca",
    "engineering",
    "reliability",
    "qa",
    "administrator",
)

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
        "fleet.read",
        "fleet.manage",
        "component.read",
        "component.manage",
        "configuration.read",
        "configuration.manage",
        "publication.read",
        "publication.manage",
        "personnel.read",
        "personnel.manage",
        "maintenance.read",
        "maintenance.manage",
        "certification.sign",
        "logbook.read",
        "signature.create",
        "task.read",
        "task.manage",
        "store.read",
        "planner.read",
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
        "fleet.read",
        "component.read",
        "configuration.read",
        "publication.read",
        "personnel.read",
        "maintenance.read",
        "certification.sign",
        "certification.release",
        "logbook.read",
        "signature.create",
        "task.read",
        "inspector.approve",
        "engineering.read",
        "qa.read",
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
        "fleet.read",
        "component.read",
        "configuration.read",
        "publication.read",
        "personnel.read",
        "maintenance.read",
        "logbook.read",
        "task.read",
        "store.read",
        "planner.read",
        "engineering.read",
    },
}

# Persona → recommended permissions (documentation + future override engine).
PERSONA_PERMISSIONS: dict[str, set[str]] = {
    "technician": {
        "publication.read",
        "component.read",
        "configuration.read",
        "fleet.read",
        "task.read",
        "task.manage",
        "maintenance.read",
        "maintenance.manage",
        "certification.sign",
        "signature.create",
        "logbook.read",
    },
    "store": {"publication.read", "component.read", "store.read", "fleet.read"},
    "planner": {"publication.read", "planner.read", "fleet.read", "maintenance.read", "task.read"},
    "inspector": {
        "publication.read",
        "maintenance.read",
        "certification.sign",
        "inspector.approve",
        "signature.create",
        "logbook.read",
        "audit.read",
        "task.read",
    },
    "aca": {
        "publication.read",
        "certification.sign",
        "certification.release",
        "signature.create",
        "logbook.read",
        "maintenance.read",
        "task.read",
    },
    "engineering": {
        "publication.read",
        "engineering.read",
        "configuration.read",
        "component.read",
        "fleet.read",
    },
    "reliability": {"publication.read", "fleet.read", "component.read", "maintenance.read", "qa.read"},
    "qa": {"qa.read", "audit.read", "publication.read", "maintenance.read", "logbook.read", "certification.sign"},
    "administrator": {"*"},
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


def persona_permissions(persona: str | None) -> set[str]:
    if not persona:
        return set()
    return set(PERSONA_PERMISSIONS.get(persona.strip().lower(), set()))
