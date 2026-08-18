"""Program 17 — Enterprise Event Fabric tests."""

from __future__ import annotations

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    r = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert r.status_code == 200
    return r.json()


def test_event_catalog_and_overview():
    login_as("operator")
    overview = client.get("/api/v1/event-fabric/overview")
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["catalog_types"] >= 50
    assert body["stored_events"] >= 5
    assert body["subscriptions"] >= 4
    assert "nervous system" in body["disclaimer"].lower() or "event" in body["disclaimer"].lower()
    catalog = client.get("/api/v1/event-fabric/catalog")
    assert catalog.status_code == 200
    codes = {c["code"] for c in catalog.json()}
    for required in (
        "UserCreated",
        "AircraftCreated",
        "ComponentInstalled",
        "WorkOrderCreated",
        "PartReceived",
        "OrderCreated",
        "CourseCompleted",
        "AuditScheduled",
        "TwinCreated",
        "RecommendationGenerated",
    ):
        assert required in codes
    twin_family = client.get("/api/v1/event-fabric/catalog", params={"family": "twin"})
    assert twin_family.status_code == 200
    assert len(twin_family.json()) >= 5


def test_publish_subscribe_dlq_retry_replay():
    login_as("operator")
    published = client.post(
        "/api/v1/event-fabric/events",
        json={
            "event_code": "ReleaseSigned",
            "payload_json": '{"work_order":"WO-EF-1","signer":"aca"}',
            "source_service": "maintenance",
            "target_service": "authority",
            "severity": "critical",
            "duration_ms": 12,
        },
    )
    assert published.status_code == 201, published.text
    event = published.json()
    assert event["event_code"] == "ReleaseSigned"
    assert event["correlation_id"]
    assert event["trace_id"]
    assert event["severity"] == "critical"

    listed = client.get("/api/v1/event-fabric/events", params={"event_code": "ReleaseSigned"})
    assert listed.status_code == 200
    assert any(e["event_id"] == event["event_id"] for e in listed.json())

    got = client.get(f"/api/v1/event-fabric/events/{event['event_id']}")
    assert got.status_code == 200

    sub = client.post(
        "/api/v1/event-fabric/subscriptions",
        json={
            "event_code": "ReleaseSigned",
            "subscriber_name": f"test-sub-{__import__('uuid').uuid4().hex[:6]}",
            "endpoint_hint": "inproc://test",
        },
    )
    assert sub.status_code == 201, sub.text

    dlq = client.post(
        "/api/v1/event-fabric/dlq",
        json={
            "store_event_id": event["event_id"],
            "subscriber_name": "failing-handler",
            "error_message": "simulated failure",
        },
    )
    assert dlq.status_code == 201, dlq.text
    dlq_id = dlq.json()["id"]
    open_dlq = client.get("/api/v1/event-fabric/dlq")
    assert open_dlq.status_code == 200
    assert any(d["id"] == dlq_id for d in open_dlq.json())

    retried = client.post(f"/api/v1/event-fabric/dlq/{dlq_id}/retry")
    assert retried.status_code == 200
    assert retried.json()["status"] == "retried"
    assert retried.json()["retry_count"] >= 1

    replay = client.post(
        "/api/v1/event-fabric/replay",
        json={"event_code": "ReleaseSigned", "limit": 10},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["events_replayed"] >= 1


def test_event_fabric_rbac_and_tenant_isolation():
    login_as("viewer")
    assert client.get("/api/v1/event-fabric/overview").status_code == 200
    assert (
        client.post(
            "/api/v1/event-fabric/events",
            json={"event_code": "UserCreated", "payload_json": "{}"},
        ).status_code
        == 403
    )
    login_as("operator")
    assert (
        client.get(
            "/api/v1/event-fabric/events", params={"organization_id": "org-aviation-west"}
        ).status_code
        == 403
    )
