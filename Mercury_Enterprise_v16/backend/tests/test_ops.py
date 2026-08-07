from app.core.event_bus import EventBus
from app.missions import MissionPriority
from app.missions.mission_service import MissionService
from app.ops.orchestrator import ResponseOrchestrationEngine
from app.timeline import TimelineManager


def test_orchestrator_escalates_high_risk_fusion_output():
    event_bus = EventBus()
    timeline_manager = TimelineManager(event_bus_instance=event_bus, max_history=50)
    mission_service = MissionService()
    mission = mission_service.create_mission(
        name="North Gate",
        description="Secure the gate",
        mission_type="security",
        created_by="ops",
        commander="captain",
        priority=MissionPriority.HIGH,
    )

    orchestrator = ResponseOrchestrationEngine(
        event_bus_instance=event_bus,
        timeline_manager=timeline_manager,
        mission_service=mission_service,
    )

    decision = orchestrator.coordinate(
        event_type="fusion.updated",
        payload={
            "track_id": "track-001",
            "fused_confidence": 92,
            "threat_level": "HIGH",
            "mission_id": mission.mission_id,
        },
        source="test",
    )

    assert decision.action == "escalate"
    assert decision.severity == "high"
    assert decision.mission_id == mission.mission_id
    assert timeline_manager.last() is not None
    assert timeline_manager.last().event_type == "ops.escalation"


def test_orchestrator_monitors_low_risk_signal():
    event_bus = EventBus()
    timeline_manager = TimelineManager(event_bus_instance=event_bus, max_history=50)
    orchestrator = ResponseOrchestrationEngine(
        event_bus_instance=event_bus,
        timeline_manager=timeline_manager,
        mission_service=MissionService(),
    )

    decision = orchestrator.coordinate(
        event_type="ai.assessed",
        payload={"confidence": 42, "level": "LOW"},
        source="test",
    )

    assert decision.action == "monitor"
    assert decision.severity == "info"
    assert timeline_manager.last() is not None
