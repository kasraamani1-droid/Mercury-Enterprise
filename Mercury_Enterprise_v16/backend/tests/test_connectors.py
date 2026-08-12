from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()


def test_connector_catalog_requires_session():
    client.post("/api/v1/auth/logout")
    unauthorized = client.get("/api/v1/connectors")
    assert unauthorized.status_code == 401

    login_as("viewer")
    response = client.get("/api/v1/connectors")
    assert response.status_code == 200
    providers = {item["provider"] for item in response.json()}
    assert {"mock-flight", "mock-weather"}.issubset(providers)


def test_connector_poll_and_events():
    login_as("operator")
    response = client.post("/api/v1/connectors/flight-demo/poll")
    assert response.status_code == 200
    assert response.json()[0]["entity_type"] == "aircraft"

    events = client.get("/api/v1/events?limit=10")
    assert events.status_code == 200
    assert any(item["event_type"] == "observation.received" for item in events.json())


def test_connector_lifecycle_start_stop_recover_and_history():
    login_as("operator")
    stopped = client.post("/api/v1/connectors/weather-demo/stop")
    assert stopped.status_code == 200
    assert stopped.json()["state"] == "offline"

    started = client.post("/api/v1/connectors/weather-demo/start")
    assert started.status_code == 200
    assert started.json()["state"] == "online"

    recovered = client.post("/api/v1/connectors/weather-demo/recover")
    assert recovered.status_code == 200
    assert recovered.json()["state"] == "online"

    history = client.get("/api/v1/connectors/weather-demo/health-history")
    assert history.status_code == 200
    states = {item["to_state"] for item in history.json()}
    assert "offline" in states
    assert "online" in states


def test_connector_manage_forbidden_for_viewer():
    login_as("viewer")
    denied = client.post("/api/v1/connectors/flight-demo/stop")
    assert denied.status_code == 403


def test_connector_lifecycle_is_audited():
    login_as("operator")
    client.post("/api/v1/connectors/flight-demo/start")
    login_as("reviewer")
    audit = client.get("/api/v1/audit", params={"action": "connector.start", "limit": 50})
    assert audit.status_code == 200
    assert any(row["target_id"] == "flight-demo" for row in audit.json())
