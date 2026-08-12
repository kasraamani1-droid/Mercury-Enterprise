from __future__ import annotations

from typing import Any

from .mission_manager import MissionManager
from .objective_manager import ObjectiveManager
from .resource_manager import ResourceManager


class MissionService:
    """High-level service coordinating mission, objective, and resource managers."""

    def __init__(self) -> None:
        self.mission_manager = MissionManager()
        self.objective_manager = ObjectiveManager()
        self.resource_manager = ResourceManager()

    def create_mission(self, *args: Any, **kwargs: Any):
        return self.mission_manager.create_mission(*args, **kwargs)

    def update_mission(self, *args: Any, **kwargs: Any):
        return self.mission_manager.update_mission(*args, **kwargs)

    def get_mission(self, mission_id: str):
        return self.mission_manager.get_mission(mission_id)

    def list_missions(self, status: str | None = None):
        return self.mission_manager.list_missions(status=status)

    def delete_mission(self, mission_id: str) -> bool:
        return self.mission_manager.delete_mission(mission_id)

    def archive_mission(self, mission_id: str):
        return self.mission_manager.archive_mission(mission_id)

    def start_mission(self, mission_id: str):
        return self.mission_manager.start_mission(mission_id)

    def pause_mission(self, mission_id: str):
        return self.mission_manager.pause_mission(mission_id)

    def resume_mission(self, mission_id: str):
        return self.mission_manager.resume_mission(mission_id)

    def complete_mission(self, mission_id: str):
        return self.mission_manager.complete_mission(mission_id)

    def cancel_mission(self, mission_id: str):
        return self.mission_manager.cancel_mission(mission_id)

    def add_note(self, mission_id: str, note: str):
        return self.mission_manager.add_note(mission_id, note)

    def assign_operator(self, mission_id: str, operator_id: str):
        return self.mission_manager.assign_operator(mission_id, operator_id)

    def remove_operator(self, mission_id: str, operator_id: str):
        return self.mission_manager.remove_operator(mission_id, operator_id)

    def create_objective(self, *args: Any, **kwargs: Any):
        return self.objective_manager.create_objective(*args, **kwargs)

    def update_objective(self, *args: Any, **kwargs: Any):
        return self.objective_manager.update_objective(*args, **kwargs)

    def complete_objective(self, objective_id: str):
        return self.objective_manager.complete_objective(objective_id)

    def cancel_objective(self, objective_id: str):
        return self.objective_manager.cancel_objective(objective_id)

    def assign_resource(self, objective_id: str, resource_id: str):
        return self.objective_manager.assign_resource(objective_id, resource_id)

    def remove_resource(self, objective_id: str, resource_id: str):
        return self.objective_manager.remove_resource(objective_id, resource_id)

    def assign_objective_operator(self, objective_id: str, operator_id: str):
        return self.objective_manager.assign_operator(objective_id, operator_id)

    def remove_objective_operator(self, objective_id: str, operator_id: str):
        return self.objective_manager.remove_operator(objective_id, operator_id)

    def list_objectives(self, mission_id: str | None = None):
        return self.objective_manager.list_objectives(mission_id)

    def register_resource(self, *args: Any, **kwargs: Any):
        return self.resource_manager.register_resource(*args, **kwargs)

    def update_resource(self, *args: Any, **kwargs: Any):
        return self.resource_manager.update_resource(*args, **kwargs)

    def get_resource(self, resource_id: str):
        return self.resource_manager.get_resource(resource_id)

    def list_resources(self):
        return self.resource_manager.list_resources()

    def assign_to_mission(self, resource_id: str, mission_id: str):
        return self.resource_manager.assign_to_mission(resource_id, mission_id)

    def release_from_mission(self, resource_id: str):
        return self.resource_manager.release_from_mission(resource_id)

    def set_available(self, resource_id: str):
        return self.resource_manager.set_available(resource_id)

    def set_active(self, resource_id: str):
        return self.resource_manager.set_active(resource_id)

    def set_offline(self, resource_id: str):
        return self.resource_manager.set_offline(resource_id)

    def set_maintenance(self, resource_id: str):
        return self.resource_manager.set_maintenance(resource_id)
