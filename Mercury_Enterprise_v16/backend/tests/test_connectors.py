from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_connector_catalog():
    response = client.get("/api/v1/connectors")
    assert response.status_code == 200
    providers = {item["provider"] for item in response.json()}
    assert {"mock-flight", "mock-weather"}.issubset(providers)


def test_connector_poll_and_events():
    response = client.post("/api/v1/connectors/flight-demo/poll")
    assert response.status_code == 200
    assert response.json()[0]["entity_type"] == "aircraft"

    events = client.get("/api/v1/events?limit=10")
    assert events.status_code == 200
    assert any(item["event_type"] == "observation.received" for item in events.json())
