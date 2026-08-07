from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from ..core.event_bus import EventBus, event_bus
from .models import MissionPriority, Objective, ObjectiveStatus

logger = logging.getLogger("mercury.missions.objectives")


class ObjectiveManager:
    """Manage objectives for missions."""

    def __init__(self, event_bus_instance: EventBus | None = None) -> None:
        self._event_bus = event_bus_instance or event_bus
        self._objectives: dict[str, Objective] = {}
        self._lock = RLock()

    def create_objective(
        self,
        mission_id: str,
        title: str,
        description: str,
        priority: MissionPriority | str = MissionPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> Objective:
        with self._lock:
            objective = Objective(
                mission_id=mission_id,
                title=title,
                description=description,
                priority=MissionPriority(priority) if isinstance(priority, str) else priority,
                metadata=metadata or {},
            )
            self._objectives[objective.objective_id] = objective
            self._publish_event("mission.objective_created", objective, {"mission_id": mission_id})
            return objective

    def update_objective(self, objective_id: str, **updates: Any) -> Objective | None:
        with self._lock:
            objective = self._objectives.get(objective_id)
            if objective is None:
                return None
            for key, value in updates.items():
                if hasattr(objective, key):
                    setattr(objective, key, value)
            objective.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.objective_updated", objective, {"objective_id": objective_id})
            return objective

    def complete_objective(self, objective_id: str) -> Objective | None:
        with self._lock:
            objective = self._objectives.get(objective_id)
            if objective is None:
                return None
            objective.status = ObjectiveStatus.COMPLETED
            objective.completed_at = datetime.now(timezone.utc)
            objective.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.objective_completed", objective, {"objective_id": objective_id})
            return objective

    def cancel_objective(self, objective_id: str) -> Objective | None:
        with self._lock:
            objective = self._objectives.get(objective_id)
            if objective is None:
                return None
            objective.status = ObjectiveStatus.CANCELLED
            objective.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.objective_updated", objective, {"objective_id": objective_id})
            return objective

    def assign_resource(self, objective_id: str, resource_id: str) -> Objective | None:
        with self._lock:
            objective = self._objectives.get(objective_id)
            if objective is None:
                return None
            if resource_id not in objective.assigned_resources:
                objective.assigned_resources.append(resource_id)
            objective.updated_at = datetime.now(timezone.utc)
            return objective

    def remove_resource(self, objective_id: str, resource_id: str) -> Objective | None:
        with self._lock:
            objective = self._objectives.get(objective_id)
            if objective is None:
                return None
            objective.assigned_resources = [value for value in objective.assigned_resources if value != resource_id]
            objective.updated_at = datetime.now(timezone.utc)
            return objective

    def assign_operator(self, objective_id: str, operator_id: str) -> Objective | None:
        with self._lock:
            objective = self._objectives.get(objective_id)
            if objective is None:
                return None
            if operator_id not in objective.assigned_operators:
                objective.assigned_operators.append(operator_id)
            objective.updated_at = datetime.now(timezone.utc)
            return objective

    def remove_operator(self, objective_id: str, operator_id: str) -> Objective | None:
        with self._lock:
            objective = self._objectives.get(objective_id)
            if objective is None:
                return None
            objective.assigned_operators = [value for value in objective.assigned_operators if value != operator_id]
            objective.updated_at = datetime.now(timezone.utc)
            return objective

    def list_objectives(self, mission_id: str | None = None) -> list[Objective]:
        with self._lock:
            objectives = list(self._objectives.values())
        if mission_id is not None:
            objectives = [objective for objective in objectives if objective.mission_id == mission_id]
        return sorted(objectives, key=lambda objective: objective.created_at)

    def _publish_event(self, event_name: str, objective: Objective, payload: dict[str, Any]) -> None:
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                loop.create_task(self._event_bus.publish(event_name, payload, source="objective_manager"))
            else:
                asyncio.run(self._event_bus.publish(event_name, payload, source="objective_manager"))
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to publish objective event event=%s objective_id=%s", event_name, objective.objective_id)

    def clear(self) -> None:
        with self._lock:
            self._objectives.clear()
