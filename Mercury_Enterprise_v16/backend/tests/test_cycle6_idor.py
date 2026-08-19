"""Cycle 6 — cross-tenant IDOR regression for aviation domains (get-by-id)."""

from __future__ import annotations

import uuid

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

WEST = "org-aviation-west"
WEST_SITE = "site-cyvr"
client = TestClient(app)


def _login(operator: str) -> None:
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text


def _switch_west() -> None:
    switched = client.post(
        "/api/v1/auth/context",
        json={"organization_id": WEST, "site_id": WEST_SITE},
    )
    assert switched.status_code == 200, switched.text


def _denied(status_code: int) -> None:
    assert status_code in {403, 404}, status_code


def test_cross_tenant_idor_aircraft_component_wo_logistics_pubs_personnel_twin():
    suffix = uuid.uuid4().hex[:8].upper()
    _login("admin")
    _switch_west()

    operator = client.post(
        "/api/v1/fleet/operators",
        json={"name": f"West Op {suffix}", "code": f"W{suffix[:5]}", "organization_id": WEST},
    )
    assert operator.status_code == 201, operator.text
    operator_id = operator.json()["id"]

    fleet = client.post(
        "/api/v1/fleet/fleets",
        json={
            "name": f"West Fleet {suffix}",
            "code": f"WF{suffix[:4]}",
            "operator_id": operator_id,
            "base_site_id": WEST_SITE,
            "organization_id": WEST,
        },
    )
    assert fleet.status_code == 201, fleet.text
    fleet_id = fleet.json()["id"]

    models = client.get("/api/v1/fleet/models").json()
    aircraft = client.post(
        "/api/v1/fleet/aircraft",
        json={
            "model_id": models[0]["id"],
            "fleet_id": fleet_id,
            "operator_id": operator_id,
            "serial_number": f"WST-{suffix}",
            "status_code": "active",
            "registration_mark": f"C-W{suffix[:3]}",
            "registration_country": "CA",
            "organization_id": WEST,
        },
    )
    assert aircraft.status_code == 201, aircraft.text
    aircraft_id = aircraft.json()["id"]
    assert aircraft.json()["organization_id"] == WEST

    catalog = client.get("/api/v1/components/catalog", params={"component_type": "engine"}).json()
    component = client.post(
        "/api/v1/components/serialized",
        json={
            "catalog_item_id": catalog[0]["id"],
            "serial_number": f"WENG-{suffix}",
            "component_status": "stores",
            "organization_id": WEST,
        },
    )
    assert component.status_code == 201, component.text
    component_id = component.json()["id"]

    employee = client.post(
        "/api/v1/personnel/employees",
        json={
            "employee_number": f"W-{suffix[:6]}",
            "full_name": f"West Tech {suffix}",
            "organization_id": WEST,
        },
    )
    assert employee.status_code == 201, employee.text
    employee_id = employee.json()["id"]

    package = client.post(
        "/api/v1/work-orders/packages",
        json={
            "aircraft_id": aircraft_id,
            "description": f"West package {suffix}",
            "priority": "normal",
            "organization_id": WEST,
        },
    )
    package_id = package.json()["id"] if package.status_code == 201 else None

    part = client.post(
        "/api/v1/logistics/parts",
        json={
            "oem_part_number": f"WPN-{suffix}",
            "description": "West consumable",
            "part_class": "consumable",
            "organization_id": WEST,
        },
    )
    assert part.status_code == 201, part.text
    part_id = part.json()["id"]

    publication = client.post(
        "/api/v1/publications",
        json={
            "publication_type_code": "SB",
            "title": f"West SB {suffix}",
            "publication_number": f"SB-W-{suffix}",
            "organization_id": WEST,
        },
    )
    assert publication.status_code == 201, publication.text
    publication_id = publication.json()["id"]

    employee_id = employee.json()["id"]

    twin = client.post(
        "/api/v1/twin/twins",
        json={
            "twin_type": "aircraft",
            "display_name": f"West twin {suffix}",
            "serial_number": f"WTWIN-{suffix}",
            "organization_id": WEST,
        },
    )
    assert twin.status_code == 201, twin.text
    twin_id = twin.json()["id"]

    line = client.post(
        "/api/v1/planning/workforce-plan-lines",
        json={
            "work_package_id": package_id,
            "employee_id": employee_id,
            "role_code": "technician",
            "organization_id": WEST,
        },
    )
    line_id = line.json()["id"] if line.status_code == 201 else None

    client.post("/api/v1/auth/logout")
    _login("operator")

    _denied(client.get(f"/api/v1/fleet/aircraft/{aircraft_id}").status_code)
    _denied(client.patch(f"/api/v1/fleet/aircraft/{aircraft_id}/status", json={"status_code": "grounded"}).status_code)
    _denied(client.get(f"/api/v1/components/serialized/{component_id}").status_code)
    if package_id:
        _denied(client.get(f"/api/v1/work-orders/packages/{package_id}").status_code)
    _denied(client.get(f"/api/v1/logistics/parts/{part_id}").status_code)
    _denied(client.get(f"/api/v1/publications/{publication_id}").status_code)
    _denied(client.get(f"/api/v1/personnel/employees/{employee_id}").status_code)
    _denied(client.get(f"/api/v1/twin/twins/{twin_id}").status_code)
    if line_id:
        _denied(client.get(f"/api/v1/planning/workforce-plan-lines/{line_id}").status_code)

    east_list = client.get("/api/v1/fleet/aircraft", params={"limit": 500})
    assert east_list.status_code == 200
    assert all(item["id"] != aircraft_id for item in east_list.json())
