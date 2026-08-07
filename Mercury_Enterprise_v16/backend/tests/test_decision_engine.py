from app.core.event_bus import EventBus
from app.decision import DecisionEngine
from app.missions import MissionPriority, MissionService


def _build_engine() -> tuple[DecisionEngine, MissionService]:
    event_bus = EventBus()
    mission_service = MissionService()
    mission_service.create_mission(
        name="North perimeter defense",
        description="Protect the airspace around the facility",
        mission_type="defense",
        created_by="ops",
        commander="Commander A",
        priority=MissionPriority.CRITICAL,
        location="North perimeter",
    )
    engine = DecisionEngine(event_bus_instance=event_bus, mission_service=mission_service)
    return engine, mission_service


def test_valid_decision_evaluation_and_ranking():
    engine, _ = _build_engine()
    result = engine.evaluate(
        {
            "mission_id": "1",
            "track_id": "track-1",
            "threat_score": 82,
            "threat_level": "high",
            "threat_confidence": 88,
            "mission_status": "active",
            "mission_priority": "critical",
            "active_alerts": [{"severity": "high", "title": "Intrusion"}],
            "available_resources": ["patrol", "camera"],
            "fused_confidence": 87,
            "response_recommendations": ["Dispatch patrol", "Escalate to operations"],
            "operator_constraints": ["avoid overreaction"],
            "environmental_context": {"weather": "clear"},
            "metadata": {"source": "pytest"},
        }
    )

    assert result["requires_human_approval"] is True
    assert result["ranked_actions"]
    assert result["selected_recommendation"]["name"]
    assert result["ranked_actions"][0]["overall_score"] >= result["ranked_actions"][-1]["overall_score"]


def test_deterministic_scoring_and_human_approval():
    engine, _ = _build_engine()
    first = engine.evaluate({"mission_id": "1", "track_id": "track-2", "threat_score": 75, "threat_level": "medium", "threat_confidence": 70, "mission_priority": "critical", "available_resources": ["patrol"], "response_recommendations": ["Track target"]})
    second = engine.evaluate({"mission_id": "1", "track_id": "track-2", "threat_score": 75, "threat_level": "medium", "threat_confidence": 70, "mission_priority": "critical", "available_resources": ["patrol"], "response_recommendations": ["Track target"]})

    assert first["confidence"] == second["confidence"]
    assert first["selected_recommendation"]["name"] == second["selected_recommendation"]["name"]
    assert first["requires_human_approval"] is True


def test_invalid_context_raises_error():
    engine, _ = _build_engine()
    try:
        engine.evaluate({"track_id": "track-3"})
    except ValueError:
        assert True
    else:
        raise AssertionError("Expected ValueError for invalid context")


def test_alerts_and_fusion_confidence_increase_score():
    engine, _ = _build_engine()
    baseline = engine.evaluate({"mission_id": "1", "track_id": "track-3", "threat_score": 60, "threat_level": "medium", "threat_confidence": 60, "mission_priority": "normal", "available_resources": ["patrol"], "response_recommendations": ["Monitor"]})
    influenced = engine.evaluate({"mission_id": "1", "track_id": "track-4", "threat_score": 60, "threat_level": "medium", "threat_confidence": 60, "mission_priority": "normal", "active_alerts": [{"severity": "high", "title": "Intrusion"}], "fused_confidence": 95, "available_resources": ["patrol"], "response_recommendations": ["Monitor"]})

    assert influenced["ranked_actions"][0]["overall_score"] > baseline["ranked_actions"][0]["overall_score"]


def test_mission_priority_and_operator_constraints_influence_ranking():
    engine, _ = _build_engine()
    normal = engine.evaluate({"mission_id": "1", "track_id": "track-5", "threat_score": 70, "threat_level": "medium", "threat_confidence": 70, "mission_priority": "normal", "available_resources": ["patrol"], "response_recommendations": ["Dispatch patrol", "Track target"], "operator_constraints": []})
    constrained = engine.evaluate({"mission_id": "1", "track_id": "track-6", "threat_score": 70, "threat_level": "medium", "threat_confidence": 70, "mission_priority": "critical", "available_resources": ["patrol"], "response_recommendations": ["Dispatch patrol", "Track target"], "operator_constraints": ["avoid overreaction"]})

    assert constrained["ranked_actions"][0]["overall_score"] >= normal["ranked_actions"][0]["overall_score"]


def test_event_bus_publishing_and_no_automatic_execution():
    event_bus = EventBus()
    mission_service = MissionService()
    mission_service.create_mission(
        name="Sample mission",
        description="Test mission",
        mission_type="defense",
        created_by="ops",
        commander="Commander B",
        priority=MissionPriority.NORMAL,
        location="Test location",
    )
    engine = DecisionEngine(event_bus_instance=event_bus, mission_service=mission_service)

    result = engine.evaluate({"mission_id": "1", "track_id": "track-7", "threat_score": 65, "threat_level": "high", "threat_confidence": 80, "mission_priority": "normal", "available_resources": ["patrol"], "response_recommendations": ["Dispatch patrol"]})

    published = [event.event_type for event in event_bus.history(limit=10)]
    assert "decision.requested" in published
    assert "decision.evaluated" in published
    assert "decision.recommendation_selected" in published
    assert result["metadata"]["automatic_execution"] is False
