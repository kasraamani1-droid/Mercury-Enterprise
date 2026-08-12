"""Sprint 6 — Aircraft Registry & Fleet Management tests."""

from __future__ import annotations

import uuid

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()


def test_seeded_catalog_and_east_fleet():
    login_as("operator")
    manufacturers = client.get("/api/v1/fleet/manufacturers")
    assert manufacturers.status_code == 200
    codes = {item["code"] for item in manufacturers.json()}
    assert "AIRBUS" in codes
    assert "BOEING" in codes

    statuses = client.get("/api/v1/fleet/statuses")
    assert statuses.status_code == 200
    assert any(item["code"] == "active" and item["is_operational"] for item in statuses.json())

    fleets = client.get("/api/v1/fleet/fleets")
    assert fleets.status_code == 200
    assert any(item["code"] == "EAST-NB" for item in fleets.json())

    aircraft = client.get("/api/v1/fleet/aircraft")
    assert aircraft.status_code == 200
    marks = {item.get("current_registration") for item in aircraft.json()}
    assert "C-GMEA" in marks


def test_fleet_org_isolation_blocks_west_for_operator():
    login_as("operator")
    denied = client.get("/api/v1/fleet/aircraft", params={"organization_id": "org-aviation-west"})
    assert denied.status_code == 403


def test_viewer_can_read_but_not_manage():
    login_as("viewer")
    assert client.get("/api/v1/fleet/aircraft").status_code == 200
    denied = client.post(
        "/api/v1/fleet/operators",
        json={"name": "No Write", "code": "NOW"},
    )
    assert denied.status_code == 403


def test_operator_can_create_aircraft_with_registration():
    suffix = uuid.uuid4().hex[:6].upper()
    login_as("operator")
    models = client.get("/api/v1/fleet/models").json()
    model_id = models[0]["id"]
    fleets = client.get("/api/v1/fleet/fleets").json()
    fleet_id = fleets[0]["id"]
    created = client.post(
        "/api/v1/fleet/aircraft",
        json={
            "model_id": model_id,
            "fleet_id": fleet_id,
            "serial_number": f"SN-{suffix}",
            "status_code": "active",
            "registration_mark": f"C-GT{suffix[:3]}",
            "registration_country": "CA",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["serial_number"] == f"SN-{suffix}"
    assert body["current_registration"] == f"C-GT{suffix[:3]}"


def test_status_update_and_duplicate_registration():
    suffix = uuid.uuid4().hex[:6].upper()
    login_as("operator")
    model_id = client.get("/api/v1/fleet/models").json()[0]["id"]
    created = client.post(
        "/api/v1/fleet/aircraft",
        json={
            "model_id": model_id,
            "serial_number": f"ST-{suffix}",
            "registration_mark": f"C-GS{suffix[:3]}",
        },
    )
    assert created.status_code == 201
    aircraft_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/fleet/aircraft/{aircraft_id}/status",
        json={"status_code": "grounded"},
    )
    assert updated.status_code == 200
    assert updated.json()["status_code"] == "grounded"

    dup = client.post(
        "/api/v1/fleet/registrations",
        json={
            "aircraft_id": aircraft_id,
            "registration_mark": f"C-GS{suffix[:3]}",
        },
    )
    assert dup.status_code == 409


def test_catalog_create_requires_admin():
    login_as("operator")
    denied = client.post(
        "/api/v1/fleet/manufacturers",
        json={"name": "Bombardier", "code": "BBD", "country": "CA"},
    )
    assert denied.status_code == 403

    login_as("admin")
    suffix = uuid.uuid4().hex[:4].upper()
    created = client.post(
        "/api/v1/fleet/manufacturers",
        json={"name": f"Maker {suffix}", "code": f"M{suffix}", "country": "CA"},
    )
    assert created.status_code == 201


def test_dashboard_fleet_health_uses_registry():
    login_as("operator")
    summary = client.get("/api/v1/dashboard/summary")
    assert summary.status_code == 200
    assert "fleet_health" in summary.json()
    assert isinstance(summary.json()["fleet_health"]["aircraft_online"], int)
    assert summary.json()["fleet_health"]["aircraft_online"] >= 1
