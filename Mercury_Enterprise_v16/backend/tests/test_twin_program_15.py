"""Program 15 — Mercury Digital Twin tests."""

from __future__ import annotations

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    r = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert r.status_code == 200
    return r.json()


def test_twin_overview_and_search():
    login_as("operator")
    overview = client.get("/api/v1/twin/overview")
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["twins"] >= 10
    assert body["by_type"].get("aircraft", 0) >= 1
    assert "not a 3d" in body["disclaimer"].lower() or "not a 3D" in body["disclaimer"]
    search = client.get("/api/v1/twin/search", params={"q": "FYXZ"})
    assert search.status_code == 200
    assert search.json()["total"] >= 1


def test_twin_passport_history_configuration_reliability():
    login_as("operator")
    twins = client.get("/api/v1/twin/twins", params={"twin_type": "aircraft"})
    assert twins.status_code == 200
    assert len(twins.json()) >= 1
    twin = twins.json()[0]
    tid = twin["id"]
    detail = client.get(f"/api/v1/twin/twins/{tid}")
    assert detail.status_code == 200
    assert detail.json()["twin_uuid"]
    assert detail.json()["history_count"] >= 1

    passport = client.get(f"/api/v1/twin/twins/{tid}/passport")
    assert passport.status_code == 200
    assert passport.json()["never_disappears"] is True
    assert passport.json()["history_immutable"] is True

    history = client.get(f"/api/v1/twin/twins/{tid}/history")
    assert history.status_code == 200
    assert len(history.json()) >= 1

    cfgs = client.get(f"/api/v1/twin/twins/{tid}/configurations")
    assert cfgs.status_code == 200
    assert len(cfgs.json()) >= 1
    assert cfgs.json()[0]["baseline"] == "current"

    rel = client.get(f"/api/v1/twin/twins/{tid}/reliability")
    assert rel.status_code == 200
    codes = {r["metric_code"] for r in rel.json()}
    assert "mtbur" in codes
    assert "dispatch_reliability" in codes
    assert all(r["architecture_only"] == "true" for r in rel.json())

    relationships = client.get(f"/api/v1/twin/twins/{tid}/relationships")
    assert relationships.status_code == 200
    assert "digital_thread_hint" in relationships.json()


def test_lifecycle_and_history_append():
    login_as("operator")
    tools = client.get("/api/v1/twin/twins", params={"twin_type": "tool"})
    assert tools.status_code == 200
    tid = tools.json()[0]["id"]
    transition = client.post(
        f"/api/v1/twin/twins/{tid}/lifecycle",
        json={"to_state": "inspected", "summary": "Calibration cycle"},
    )
    assert transition.status_code == 200, transition.text
    assert transition.json()["lifecycle_state"] == "inspected"
    hist = client.post(
        f"/api/v1/twin/twins/{tid}/history",
        json={
            "history_kind": "inspection",
            "title": "Visual inspection",
            "summary": "Passed",
        },
    )
    assert hist.status_code == 201, hist.text


def test_twin_rbac_and_tenant_isolation():
    login_as("viewer")
    assert client.get("/api/v1/twin/overview").status_code == 200
    assert (
        client.post(
            "/api/v1/twin/twins",
            json={"twin_type": "tool", "display_name": "Nope", "serial_number": "X"},
        ).status_code
        == 403
    )
    login_as("operator")
    assert (
        client.get("/api/v1/twin/twins", params={"organization_id": "org-aviation-west"}).status_code
        == 403
    )
