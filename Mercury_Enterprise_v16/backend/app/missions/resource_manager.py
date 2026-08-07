from __future__ import annotations

import asyncio
import logging
from threading import RLock

from ..core.event_bus import EventBus, event_bus
from .models import Resource, ResourceStatus

logger = logging.getLogger("mercury.missions.resources")


class ResourceManager:
    """Manage operational assets and mission assignments."""

    def __init__(self, event_bus_instance: EventBus | None = None) -> None:
        self._event_bus = event_bus_instance or event_bus
        self._resources: dict[str, Resource] = {}
        self._lock = RLock()

    def register_resource(self, name: str, resource_type: str, organization: str = "", location: str = "", capabilities: list[str] | None = None, metadata: dict | None = None) -> Resource:
        with self._lock:
            resource = Resource(
                name=name,
                resource_type=resource_type,
                organization=organization,
                location=location,
                capabilities=capabilities or [],
                metadata=metadata or {},
            )
            self._resources[resource.resource_id] = resource
            self._publish_event("mission.resource_assigned", resource, {"resource_id": resource.resource_id})
            return resource

    def update_resource(self, resource_id: str, **updates) -> Resource | None:
        with self._lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return None
            for key, value in updates.items():
                if hasattr(resource, key):
                    setattr(resource, key, value)
            return resource

    def get_resource(self, resource_id: str) -> Resource | None:
        with self._lock:
            return self._resources.get(resource_id)

    def list_resources(self) -> list[Resource]:
        with self._lock:
            return list(self._resources.values())

    def assign_to_mission(self, resource_id: str, mission_id: str) -> Resource | None:
        with self._lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return None
            resource.status = ResourceStatus.ASSIGNED
            resource.assigned_mission = mission_id
            self._publish_event("mission.resource_assigned", resource, {"resource_id": resource_id, "mission_id": mission_id})
            return resource

    def release_from_mission(self, resource_id: str) -> Resource | None:
        with self._lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return None
            resource.status = ResourceStatus.AVAILABLE
            resource.assigned_mission = None
            self._publish_event("mission.resource_released", resource, {"resource_id": resource_id})
            return resource

    def set_available(self, resource_id: str) -> Resource | None:
        with self._lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return None
            resource.status = ResourceStatus.AVAILABLE
            return resource

    def set_active(self, resource_id: str) -> Resource | None:
        with self._lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return None
            resource.status = ResourceStatus.ACTIVE
            return resource

    def set_offline(self, resource_id: str) -> Resource | None:
        with self._lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return None
            resource.status = ResourceStatus.OFFLINE
            return resource

    def set_maintenance(self, resource_id: str) -> Resource | None:
        with self._lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return None
            resource.status = ResourceStatus.MAINTENANCE
            return resource

    def _publish_event(self, event_name: str, resource: Resource, payload: dict) -> None:
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                loop.create_task(self._event_bus.publish(event_name, payload, source="resource_manager"))
            else:
                asyncio.run(self._event_bus.publish(event_name, payload, source="resource_manager"))
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to publish resource event event=%s resource_id=%s", event_name, resource.resource_id)

    def clear(self) -> None:
        with self._lock:
            self._resources.clear()
