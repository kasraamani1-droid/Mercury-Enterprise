"""Closed-loop C-GMEA pilot walk on existing APIs. SIM / demo — not production certification."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from conftest import TEST_AUTH_PASSWORD

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PACKAGE_ROOT / "frontend"
WE = FRONTEND / "js" / "workspace-engine"

client = TestClient(app)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def login(operator: str) -> None:
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text


def test_pr8_through_pr14_contracts_still_present() -> None:
    render = _read(WE / "render.js")
    cfg = _read(WE / "configuration.js")
    ops = _read(WE / "maintenance-ops.js")
    log = _read(WE / "logistics-ops.js")
    plan = _read(WE / "planning-ops.js")
    pubs = _read(WE / "publications-ops.js")
    pers = _read(WE / "personnel-ops.js")
    twin = _read(WE / "twin-ops.js")
    html = _read(FRONTEND / "index.html")
    assert "renderAircraftConfigurationPanel" in cfg or "bindConfigurationPanel" in cfg
    assert "bindMaintenanceOpsPanel" in ops
    assert "bindLogisticsOpsPanel" in log
    assert "renderFindingWorkspace" in plan
    assert "renderPublicationWorkspace" in pubs
    assert "renderEmployeeWorkspace" in pers
    assert "renderTwinOverview" in twin
    assert 'id="workOrdersWorkspace"' in html
    assert 'id="logisticsWorkspace"' in html
    assert 'id="planningWorkspace"' in html
    assert 'id="planWorkforce"' in html
    assert "SIM / demo data" in html


def test_closed_loop_c_gmea_api_walk() -> None:
    login("operator")

    live = client.get("/live")
    ready = client.get("/api/v1/ready")
    assert live.status_code == 200, live.text
    assert ready.status_code == 200, ready.text

    aircraft = client.get("/api/v1/fleet/aircraft/ac-c-gmea")
    assert aircraft.status_code == 200, aircraft.text
    body = aircraft.json()
    assert body["id"] == "ac-c-gmea"
    assert "GMEA" in str(body.get("current_registration") or "").upper()

    config = client.get("/api/v1/components/aircraft/ac-c-gmea/configuration")
    assert config.status_code == 200, config.text

    checks = client.get("/api/v1/planning/checks", params={"aircraft_id": "ac-c-gmea", "limit": 20})
    assert checks.status_code == 200, checks.text
    assert checks.json()
    assert all(row["aircraft_id"] == "ac-c-gmea" for row in checks.json())

    programs = client.get("/api/v1/planning/programs")
    assert programs.status_code == 200
    assert any(row["program_code"] == "MP-A320-LINE" for row in programs.json())

    employees = client.get("/api/v1/personnel/employees", params={"limit": 80})
    assert employees.status_code == 200, employees.text
    numbers = {row["employee_number"] for row in employees.json()}
    assert {"E-1001", "E-2001", "E-3001"} <= numbers

    pubs = client.get("/api/v1/publications/by-aircraft/ac-c-gmea")
    assert pubs.status_code == 200, pubs.text

    packages = client.get("/api/v1/work-orders/packages", params={"aircraft_id": "ac-c-gmea", "limit": 20})
    assert packages.status_code == 200, packages.text
    demo = next((row for row in packages.json() if row["package_number"] == "WP-DEMO-001"), None)
    assert demo is not None
    assert demo["aircraft_id"] == "ac-c-gmea"

    workforce = client.get("/api/v1/planning/workforce-plan-lines", params={"work_package_id": demo["id"]})
    assert workforce.status_code == 200, workforce.text
    assert workforce.json()
    line = client.get(f"/api/v1/planning/workforce-plan-lines/{workforce.json()[0]['id']}")
    assert line.status_code == 200

    orders = client.get("/api/v1/work-orders/orders", params={"aircraft_id": "ac-c-gmea", "limit": 20})
    assert orders.status_code == 200
    assert any(row.get("wo_number") == "WO-DEMO-7100" for row in orders.json())

    cards = client.get("/api/v1/work-orders/job-cards", params={"aircraft_id": "ac-c-gmea", "limit": 20})
    assert cards.status_code == 200
    assert cards.json()

    logbook = client.get("/api/v1/maintenance/logbook", params={"aircraft_id": "ac-c-gmea", "limit": 20})
    assert logbook.status_code == 200

    logistics = client.get("/api/v1/logistics/dashboard")
    assert logistics.status_code == 200, logistics.text

    twins = client.get("/api/v1/twin/twins", params={"limit": 50})
    assert twins.status_code == 200, twins.text

    login("viewer")
    assert client.get("/api/v1/fleet/aircraft/ac-c-gmea").status_code == 200
    assert client.get("/api/v1/planning/workforce-plan-lines").status_code == 200
    assert (
        client.post(
            "/api/v1/planning/workforce-plan-lines",
            json={"employee_id": "pers-op-east-001", "role_code": "technician", "work_package_id": demo["id"]},
        ).status_code
        == 403
    )
