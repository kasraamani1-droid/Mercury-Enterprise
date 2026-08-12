from conftest import TEST_AUTH_PASSWORD
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


def test_ops_router_reuses_main_orchestrator_singleton():
    from app.main import response_orchestrator
    from app.routers.ops import get_response_orchestrator

    assert get_response_orchestrator() is response_orchestrator


def test_ops_coordinate_requires_auth():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    client.post("/api/v1/auth/logout")
    denied = client.post("/api/v1/ops/coordinate", json={"event_type": "test", "payload": {}})
    assert denied.status_code == 401

    login = client.post("/api/v1/auth/login", json={"operator": "viewer", "password": TEST_AUTH_PASSWORD})
    assert login.status_code == 200
    forbidden = client.post("/api/v1/ops/coordinate", json={"event_type": "test", "payload": {}})
    assert forbidden.status_code == 403

    login = client.post("/api/v1/auth/login", json={"operator": "operator", "password": TEST_AUTH_PASSWORD})
    assert login.status_code == 200
    allowed = client.post(
        "/api/v1/ops/coordinate",
        json={"event_type": "ai.assessed", "payload": {"confidence": 40, "level": "LOW"}},
    )
    assert allowed.status_code == 200
    assert "action" in allowed.json()
