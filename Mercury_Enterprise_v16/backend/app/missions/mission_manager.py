from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from ..core.event_bus import EventBus, event_bus
from .models import Mission, MissionPriority, MissionStatus

logger = logging.getLogger("mercury.missions.manager")


class MissionManager:
    """Manage mission lifecycle and mission state in memory."""

    def __init__(self, event_bus_instance: EventBus | None = None) -> None:
        self._event_bus = event_bus_instance or event_bus
        self._missions: dict[str, Mission] = {}
        self._lock = RLock()

    def create_mission(
        self,
        name: str,
        description: str,
        mission_type: str,
        created_by: str,
        commander: str,
        priority: MissionPriority | str = MissionPriority.NORMAL,
        location: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Mission:
        with self._lock:
            mission = Mission(
                name=name,
                description=description,
                mission_type=mission_type,
                created_by=created_by,
                commander=commander,
                status=MissionStatus.DRAFT,
                priority=MissionPriority(priority) if isinstance(priority, str) else priority,
                location=location,
                metadata=metadata or {},
            )
            self._missions[mission.mission_id] = mission
            self._publish_event("mission.created", mission, {"name": mission.name})
            return mission

    def update_mission(self, mission_id: str, **updates: Any) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            for key, value in updates.items():
                if hasattr(mission, key):
                    setattr(mission, key, value)
            mission.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.updated", mission, {"mission_id": mission_id})
            return mission

    def get_mission(self, mission_id: str) -> Mission | None:
        with self._lock:
            return self._missions.get(mission_id)

    def list_missions(self, status: MissionStatus | str | None = None) -> list[Mission]:
        with self._lock:
            missions = list(self._missions.values())
        if status is not None:
            target_status = MissionStatus(status) if isinstance(status, str) else status
            missions = [mission for mission in missions if mission.status == target_status]
        return sorted(missions, key=lambda mission: mission.created_at, reverse=True)

    def delete_mission(self, mission_id: str) -> bool:
        with self._lock:
            return self._missions.pop(mission_id, None) is not None

    def archive_mission(self, mission_id: str) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            mission.status = MissionStatus.ARCHIVED
            mission.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.archived", mission, {"mission_id": mission_id})
            return mission

    def start_mission(self, mission_id: str) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            if mission.status not in {MissionStatus.DRAFT, MissionStatus.PLANNED, MissionStatus.READY, MissionStatus.PAUSED}:
                return mission
            mission.status = MissionStatus.ACTIVE
            mission.started_at = datetime.now(timezone.utc)
            mission.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.started", mission, {"mission_id": mission_id})
            return mission

    def pause_mission(self, mission_id: str) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            if mission.status != MissionStatus.ACTIVE:
                return mission
            mission.status = MissionStatus.PAUSED
            mission.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.paused", mission, {"mission_id": mission_id})
            return mission

    def resume_mission(self, mission_id: str) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            if mission.status != MissionStatus.PAUSED:
                return mission
            mission.status = MissionStatus.ACTIVE
            mission.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.resumed", mission, {"mission_id": mission_id})
            return mission

    def complete_mission(self, mission_id: str) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            mission.status = MissionStatus.COMPLETED
            mission.completed_at = datetime.now(timezone.utc)
            mission.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.completed", mission, {"mission_id": mission_id})
            return mission

    def cancel_mission(self, mission_id: str) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            mission.status = MissionStatus.CANCELLED
            mission.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.cancelled", mission, {"mission_id": mission_id})
            return mission

    def add_note(self, mission_id: str, note: str) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            mission.notes.append(note)
            mission.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.updated", mission, {"mission_id": mission_id, "note": note})
            return mission

    def assign_operator(self, mission_id: str, operator_id: str) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            if operator_id not in mission.assigned_operators:
                mission.assigned_operators.append(operator_id)
            mission.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.operator_assigned", mission, {"operator_id": operator_id})
            return mission

    def remove_operator(self, mission_id: str, operator_id: str) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            mission.assigned_operators = [value for value in mission.assigned_operators if value != operator_id]
            mission.updated_at = datetime.now(timezone.utc)
            self._publish_event("mission.operator_removed", mission, {"operator_id": operator_id})
            return mission

    def _publish_event(self, event_name: str, mission: Mission, payload: dict[str, Any]) -> None:
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                loop.create_task(self._event_bus.publish(event_name, payload, source="mission_manager"))
            else:
                asyncio.run(self._event_bus.publish(event_name, payload, source="mission_manager"))
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to publish mission event event=%s mission_id=%s", event_name, mission.mission_id)

    def clear(self) -> None:
        with self._lock:
            self._missions.clear()
