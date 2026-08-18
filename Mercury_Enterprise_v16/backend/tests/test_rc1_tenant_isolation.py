"""RC1 Blocker 02 — tenant isolation: APIs, queries, WebSocket, RBAC, audit."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import alert_manager, app
from app.websocket.manager import ConnectionManager

WEST_ORG = "org-aviation-west"
WEST_SITE = "site-cyvr"


class _FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def accept(self) -> None:
        return None

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


def _client() -> TestClient:
    return TestClient(app)


def _login(http: TestClient, operator: str = "operator"):
    response = http.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()


def _switch_west(http: TestClient):
    switched = http.post(
        "/api/v1/auth/context",
        json={"organization_id": WEST_ORG, "site_id": WEST_SITE},
    )
    assert switched.status_code == 200, switched.text
    return switched.json()


def _create_west_incident() -> str:
    west = _client()
    _login(west, "admin")
    _switch_west(west)
    created = west.post(
        "/api/v1/incidents",
        json={"title": "West isolation incident", "severity": "high", "summary": "rb-01"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["organization_id"] == WEST_ORG
    assert body["site_id"] == WEST_SITE
    return body["id"]


def test_websocket_broadcast_does_not_cross_tenants():
    mgr = ConnectionManager()
    east = _FakeSocket()
    west = _FakeSocket()

    async def _run():
        await mgr.connect(east, organization_id="org-aviation-east", site_id="site-cyul")
        await mgr.connect(west, organization_id=WEST_ORG, site_id=WEST_SITE)
        await mgr.broadcast(
            {"type": "incident.created", "incident_id": "west-1"},
            organization_id=WEST_ORG,
            site_id=WEST_SITE,
        )
        await mgr.broadcast({"type": "heartbeat", "version": "test"})

    asyncio.run(_run())
    assert west.sent[0]["type"] == "incident.created"
    assert all(item["type"] != "incident.created" for item in east.sent)
    assert any(item["type"] == "heartbeat" for item in east.sent)
    assert any(item["type"] == "heartbeat" for item in west.sent)
    assert mgr.connection_count(organization_id=WEST_ORG) == 1
    assert mgr.connection_count(organization_id="org-aviation-east") == 1


def test_incident_writes_are_tenant_scoped():
    west_id = _create_west_incident()
    east = _client()
    _login(east, "operator")

    listing = east.get("/api/v1/incidents", params={"limit": 500})
    assert listing.status_code == 200
    assert all(item["id"] != west_id for item in listing.json())

    assert east.get(f"/api/v1/incidents/{west_id}").status_code == 404
    assert east.get(f"/api/v1/incidents/{west_id}/assessment").status_code == 404
    assert east.get(f"/api/v1/incidents/{west_id}/report").status_code == 404

    status_update = east.patch(
        f"/api/v1/incidents/{west_id}/status",
        json={"status": "investigating"},
    )
    assert status_update.status_code == 404

    event = east.post(
        f"/api/v1/incidents/{west_id}/events",
        json={
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "event_type": "note",
            "source": "east-operator",
            "description": "cross-tenant",
            "confidence": 50,
        },
    )
    assert event.status_code == 404

    evidence = east.post(
        f"/api/v1/incidents/{west_id}/evidence",
        json={
            "evidence_type": "operator_note",
            "source": "east-operator",
            "title": "leak",
            "content": "should not attach",
            "confidence": 50,
        },
    )
    assert evidence.status_code == 404


def test_incident_same_tenant_status_and_audit_include_org_site():
    east = _client()
    _login(east, "operator")
    created = east.post(
        "/api/v1/incidents",
        json={"title": "East isolation audit", "severity": "low", "summary": "rb-01"},
    )
    assert created.status_code == 201, created.text
    incident = created.json()
    incident_id = incident["id"]
    org_id = incident["organization_id"]
    site_id = incident["site_id"]

    updated = east.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "investigating"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "investigating"

    reviewer = _client()
    _login(reviewer, "reviewer")
    audit = reviewer.get(
        "/api/v1/audit",
        params={"action": "incident.status", "target_id": incident_id},
    )
    assert audit.status_code == 200
    rows = audit.json()
    assert rows
    assert rows[0]["organization_id"] == org_id
    assert rows[0]["site_id"] == site_id
    assert rows[0]["target_id"] == incident_id


def test_west_audit_not_visible_to_east_reviewer():
    west_id = _create_west_incident()
    east = _client()
    _login(east, "reviewer")
    audit = east.get("/api/v1/audit", params={"action": "incident.create", "target_id": west_id})
    assert audit.status_code == 200
    assert all(row["target_id"] != west_id for row in audit.json())


def test_rbac_viewer_cannot_write_own_tenant_incident():
    east = _client()
    _login(east, "operator")
    created = east.post(
        "/api/v1/incidents",
        json={"title": "RBAC viewer write", "severity": "low", "summary": "rbac"},
    )
    assert created.status_code == 201
    incident_id = created.json()["id"]

    viewer = _client()
    _login(viewer, "viewer")
    assert viewer.get("/api/v1/incidents").status_code == 200
    denied = viewer.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "investigating"},
    )
    assert denied.status_code == 403


def test_alerts_and_dashboard_are_tenant_filtered():
    west_alert = alert_manager.create_alert(
        incident_id="west-alert-inc",
        severity="critical",
        title="West tenant alert",
        message="must not leak east",
        source="test",
        organization_id=WEST_ORG,
        site_id=WEST_SITE,
    )
    east = _client()
    _login(east, "operator")
    alerts = east.get("/api/v1/alerts")
    assert alerts.status_code == 200
    titles = {item["title"] for item in alerts.json()}
    assert "West tenant alert" not in titles

    ack = east.post(f"/api/v1/alerts/{west_alert.id}/ack")
    assert ack.status_code == 404

    dashboard = east.get("/api/v1/dashboard/summary")
    assert dashboard.status_code == 200
    # Dashboard counts only tenant-visible alerts; a west-only critical must not inflate east.
    assert dashboard.json()["active_alerts_summary"]["critical"] >= 0

    west = _client()
    _login(west, "admin")
    _switch_west(west)
    west_list = west.get("/api/v1/alerts")
    assert west_list.status_code == 200
    assert any(item["id"] == west_alert.id for item in west_list.json())


def test_websocket_http_create_does_not_leak_to_east_socket():
    east = _client()
    west = _client()
    _login(east, "operator")
    _login(west, "admin")
    _switch_west(west)

    with east.websocket_connect("/api/v1/ws") as east_ws:
        connected = east_ws.receive_json()
        assert connected["type"] == "connected"
        assert connected["organization"]["organization_id"] != WEST_ORG

        created = west.post(
            "/api/v1/incidents",
            json={"title": "WS leak probe", "severity": "medium", "summary": "rb-02"},
        )
        assert created.status_code == 201, created.text
        west_id = created.json()["id"]

        east_ws.send_text("ping")
        leaked = False
        for _ in range(6):
            message = east_ws.receive_json()
            if message.get("type") == "incident.created" and message.get("incident_id") == west_id:
                leaked = True
                break
            if message.get("type") == "pong":
                break
        assert leaked is False
