from app.missions import MissionPriority, MissionStatus, ObjectiveStatus, ResourceStatus
from app.missions.mission_service import MissionService


def test_mission_lifecycle_and_notes():
    service = MissionService()

    mission = service.create_mission(
        name="Operation Harbor Shield",
        description="Secure the harbor perimeter",
        mission_type="security",
        created_by="ops",
        commander="captain",
        priority=MissionPriority.HIGH,
        location="Harbor",
    )

    assert mission.status == MissionStatus.DRAFT
    assert service.get_mission(mission.mission_id) is mission

    updated = service.update_mission(mission.mission_id, location="Harbor North")
    assert updated is not None
    assert updated.location == "Harbor North"

    service.add_note(mission.mission_id, "First briefing complete")
    assert "First briefing complete" in service.get_mission(mission.mission_id).notes

    started = service.start_mission(mission.mission_id)
    assert started is not None
    assert started.status == MissionStatus.ACTIVE

    paused = service.pause_mission(mission.mission_id)
    assert paused is not None
    assert paused.status == MissionStatus.PAUSED

    resumed = service.resume_mission(mission.mission_id)
    assert resumed is not None
    assert resumed.status == MissionStatus.ACTIVE

    completed = service.complete_mission(mission.mission_id)
    assert completed is not None
    assert completed.status == MissionStatus.COMPLETED


def test_objective_and_resource_management():
    service = MissionService()

    mission = service.create_mission(
        name="Recon Sweep",
        description="Sweep the northern corridor",
        mission_type="recon",
        created_by="ops",
        commander="lieutenant",
    )

    objective = service.create_objective(
        mission_id=mission.mission_id,
        title="Identify ingress points",
        description="Map likely ingress points",
        priority=MissionPriority.NORMAL,
    )
    assert objective.status == ObjectiveStatus.PENDING

    service.assign_objective_operator(objective.objective_id, "operator-1")
    assert "operator-1" in objective.assigned_operators

    resource = service.register_resource(name="Drone-1", resource_type="uav", capabilities=["surveillance"])
    assert resource.status == ResourceStatus.AVAILABLE

    service.assign_to_mission(resource.resource_id, mission.mission_id)
    updated_resource = service.get_resource(resource.resource_id)
    assert updated_resource is not None
    assert updated_resource.status == ResourceStatus.ASSIGNED
    assert updated_resource.assigned_mission == mission.mission_id

    service.assign_resource(objective.objective_id, resource.resource_id)
    assert resource.resource_id in objective.assigned_resources

    completed_objective = service.complete_objective(objective.objective_id)
    assert completed_objective is not None
    assert completed_objective.status == ObjectiveStatus.COMPLETED
