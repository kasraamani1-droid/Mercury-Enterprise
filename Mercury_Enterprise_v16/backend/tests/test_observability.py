from conftest import TEST_AUTH_PASSWORD
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.health import build_health_payload, build_ready_payload
from app.main import app

client = TestClient(app)


def test_health_includes_additive_diagnostics():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["version"] == "16.0.0"
    assert "database" in body
    assert "connectors" in body
    assert body["decision_support"]["advisory_only"] is True
    assert "checks" in body
    assert "password" not in str(body).lower()
    assert "secret" not in str(body).lower()


def test_ready_ok_when_database_available():
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["checks"]["database"] == "ok"


def test_ready_fails_when_database_check_errors():
    db = MagicMock()
    db.execute.side_effect = RuntimeError("db down")
    try:
        build_ready_payload(db)
        raise AssertionError("Expected HTTPException")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 503
        detail = exc.detail
        assert detail["ready"] is False
        assert detail["reason"] == "database"


def test_health_payload_marks_degraded_on_db_error():
    db = MagicMock()
    db.execute.side_effect = RuntimeError("db down")
    manager = MagicMock()
    manager.list_records.return_value = []
    payload = build_health_payload(db, manager)
    assert payload["status"] == "degraded"
    assert payload["database"] == "error"
    assert payload["checks"]["database"] == "error"


def test_platform_status_uses_advisory_ai_signal():
    login = client.post("/api/v1/auth/login", json={"operator": "operator", "password": TEST_AUTH_PASSWORD})
    assert login.status_code == 200
    response = client.get("/api/v1/platform/status")
    assert response.status_code == 200
    body = response.json()
    assert body["services"]["ai"] == "decision_engine_advisory"
    assert body["services"]["events"] == "in-process"
    assert "connectors" in body
    assert body["decision_support"]["advisory_only"] is True


def test_ops_health_includes_subsystem_fields():
    login = client.post("/api/v1/auth/login", json={"operator": "operator", "password": TEST_AUTH_PASSWORD})
    assert login.status_code == 200
    response = client.get("/api/v1/ops/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "connectors" in body
    assert body["advisory_only"] is True


def test_decision_evaluate_survives_connector_noise():
    login = client.post("/api/v1/auth/login", json={"operator": "operator", "password": TEST_AUTH_PASSWORD})
    assert login.status_code == 200
    response = client.post(
        "/api/v1/decisions/evaluate",
        json={
            "mission_id": "mission-obs-1",
            "track_id": "track-obs-1",
            "threat_level": "medium",
            "threat_score": 55,
            "response_recommendations": ["Monitor current state"],
        },
    )
    assert response.status_code == 200
    assert response.json()["requires_human_approval"] is True
