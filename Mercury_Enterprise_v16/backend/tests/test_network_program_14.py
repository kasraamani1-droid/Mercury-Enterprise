"""Program 14 — Mercury Aviation Network tests."""

from __future__ import annotations

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    r = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert r.status_code == 200
    return r.json()


def test_network_overview_and_directory():
    login_as("operator")
    overview = client.get("/api/v1/network/overview")
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["org_profiles"] >= 5
    assert body["professionals"] >= 4
    assert body["partnerships"] >= 1
    assert body["collaborations"] >= 1
    assert body["events"] >= 3
    assert "not social media" in body["disclaimer"].lower()
    search = client.get("/api/v1/network/directory/search", params={"q": "AME"})
    assert search.status_code == 200
    assert search.json()["total"] >= 1


def test_partnership_gated_collaboration_messaging_docs():
    login_as("operator")
    partnerships = client.get("/api/v1/network/partnerships")
    assert partnerships.status_code == 200
    assert any(p["status"] == "active" for p in partnerships.json())

    # Cross-org without partnership to a random org must fail
    blocked = client.post(
        "/api/v1/network/collaborations",
        json={
            "partner_organization_id": "org-does-not-exist-partner",
            "collaboration_type": "technical_assistance",
            "title": "Should fail",
        },
    )
    assert blocked.status_code == 403

    collab = client.post(
        "/api/v1/network/collaborations",
        json={
            "partner_organization_id": "org-aviation-west",
            "collaboration_type": "repair_quotation",
            "title": "Repair quotation request",
            "summary": "Avionics unit",
        },
    )
    assert collab.status_code == 201, collab.text

    share = client.post(
        "/api/v1/network/document-shares",
        json={
            "partner_organization_id": "org-aviation-west",
            "document_ref": "pub://AMM-B737-REV12",
            "title": "AMM excerpt",
            "share_mode": "read_only",
            "watermark": True,
            "download_allowed": False,
        },
    )
    assert share.status_code == 201, share.text
    assert share.json()["watermark"] == "true"

    thread = client.post(
        "/api/v1/network/threads",
        json={
            "partner_organization_id": "org-aviation-west",
            "scope": "org_to_org",
            "subject": "Engineering support thread",
        },
    )
    assert thread.status_code == 201, thread.text
    tid = thread.json()["id"]
    msg = client.post(
        "/api/v1/network/messages",
        json={"thread_id": tid, "body": "Please review the attachment ref."},
    )
    assert msg.status_code == 201
    msgs = client.get(f"/api/v1/network/threads/{tid}/messages")
    assert msgs.status_code == 200
    assert len(msgs.json()) >= 1


def test_professionals_events_and_rbac():
    login_as("viewer")
    assert client.get("/api/v1/network/overview").status_code == 200
    assert (
        client.post(
            "/api/v1/network/events",
            json={"event_type": "webinar", "title": "Nope"},
        ).status_code
        == 403
    )
    login_as("operator")
    events = client.get("/api/v1/network/events")
    assert events.status_code == 200
    assert len(events.json()) >= 3
    created = client.post(
        "/api/v1/network/events",
        json={
            "event_type": "conference",
            "title": f"Network Summit {__import__('uuid').uuid4().hex[:6]}",
            "summary": "Professional aviation collaboration",
        },
    )
    assert created.status_code == 201, created.text
    profs = client.get("/api/v1/network/professionals")
    assert profs.status_code == 200
    assert len(profs.json()) >= 4


def test_network_tenant_isolation():
    login_as("operator")
    assert (
        client.get("/api/v1/network/partnerships", params={"organization_id": "org-aviation-west"}).status_code
        == 403
    )
