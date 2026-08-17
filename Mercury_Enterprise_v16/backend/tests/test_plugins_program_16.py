"""Program 16 — Mercury Plugin Platform tests."""

from __future__ import annotations

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    r = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert r.status_code == 200
    return r.json()


def test_plugins_catalog_seeded():
    login_as("operator")
    overview = client.get("/api/v1/plugins/overview")
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["plugins"] >= 11
    assert body["installations"] >= 6
    assert body["dashboards"] >= 1
    assert "safety management" in body["disclaimer"].lower()
    catalog = client.get("/api/v1/plugins/catalog")
    assert catalog.status_code == 200
    codes = {p["code"] for p in catalog.json()}
    for required in (
        "garmin",
        "honeywell",
        "drone_inspection",
        "ndt",
        "flight_ops",
        "accounting",
        "custom_dashboards",
        "erp",
        "sms",
        "weather",
        "fuel_planning",
    ):
        assert required in codes
    sms = client.get("/api/v1/plugins/catalog/sms")
    assert sms.status_code == 200
    assert "safety" in sms.json()["name"].lower() or "safety" in sms.json()["disclaimer"].lower()


def test_install_and_dashboard():
    login_as("operator")
    # honeywell may not be pre-installed
    created = client.post(
        "/api/v1/plugins/installations",
        json={
            "plugin_code": "honeywell",
            "install_status": "installed",
            "config_ref": "vault://plugins/org-aviation-east/honeywell",
        },
    )
    assert created.status_code in {201, 409}, created.text
    installs = client.get("/api/v1/plugins/installations")
    assert installs.status_code == 200
    assert any(i["plugin_code"] == "honeywell" for i in installs.json()) or created.status_code == 201

    dash = client.post(
        "/api/v1/plugins/dashboards",
        json={
            "name": f"Fuel Desk {__import__('uuid').uuid4().hex[:6]}",
            "widgets_json": '[{"id":"fuel","type":"fuel_planning","title":"Fuel"}]',
        },
    )
    assert dash.status_code == 201, dash.text
    listed = client.get("/api/v1/plugins/dashboards")
    assert listed.status_code == 200
    assert len(listed.json()) >= 2


def test_connect_extra_connectors_present():
    login_as("operator")
    connectors = client.get("/api/v1/connect/connectors")
    assert connectors.status_code == 200
    codes = {c["code"] for c in connectors.json()}
    for required in (
        "oem.garmin",
        "oem.honeywell",
        "inspection.drone",
        "ndt.generic",
        "dashboard.custom",
        "safety.sms",
        "fuel.planning",
        "erp.generic",
        "accounting.generic",
        "weather.generic",
        "flight_ops.generic",
    ):
        assert required in codes


def test_plugins_rbac_and_tenant_isolation():
    login_as("viewer")
    assert client.get("/api/v1/plugins/overview").status_code == 200
    assert (
        client.post(
            "/api/v1/plugins/installations",
            json={"plugin_code": "fuel_planning"},
        ).status_code
        == 403
    )
    login_as("operator")
    assert (
        client.get(
            "/api/v1/plugins/installations", params={"organization_id": "org-aviation-west"}
        ).status_code
        == 403
    )
