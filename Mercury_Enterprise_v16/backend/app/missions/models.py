from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class MissionStatus(StrEnum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    READY = "READY"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class MissionPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ObjectiveStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ResourceStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    ACTIVE = "ACTIVE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"


@dataclass(slots=True)
class Objective:
    objective_id: str = field(default_factory=lambda: str(uuid4()))
    mission_id: str = ""
    title: str = ""
    description: str = ""
    priority: MissionPriority = MissionPriority.NORMAL
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    assigned_resources: list[str] = field(default_factory=list)
    assigned_operators: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "mission_id": self.mission_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_resources": self.assigned_resources,
            "assigned_operators": self.assigned_operators,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class Resource:
    resource_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    resource_type: str = ""
    status: ResourceStatus = ResourceStatus.AVAILABLE
    organization: str = ""
    location: str = ""
    capabilities: list[str] = field(default_factory=list)
    assigned_mission: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "resource_type": self.resource_type,
            "status": self.status.value,
            "organization": self.organization,
            "location": self.location,
            "capabilities": self.capabilities,
            "assigned_mission": self.assigned_mission,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class Mission:
    mission_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    mission_type: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: str = ""
    commander: str = ""
    status: MissionStatus = MissionStatus.DRAFT
    priority: MissionPriority = MissionPriority.NORMAL
    location: str = ""
    objectives: list[Objective] = field(default_factory=list)
    assigned_resources: list[str] = field(default_factory=list)
    assigned_operators: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "name": self.name,
            "description": self.description,
            "mission_type": self.mission_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by,
            "commander": self.commander,
            "status": self.status.value,
            "priority": self.priority.value,
            "location": self.location,
            "objectives": [obj.to_dict() for obj in self.objectives],
            "assigned_resources": self.assigned_resources,
            "assigned_operators": self.assigned_operators,
            "notes": self.notes,
            "metadata": self.metadata,
        }
