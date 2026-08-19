"""Maintenance planning operator UI contracts and live API workflows.

No Playwright. Verifies Planning Ops / Engineering / Workspace Engine
against existing FastAPI planning routes. Preserves PR #8–#11 operator UI.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from conftest import TEST_AUTH_PASSWORD

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PACKAGE_ROOT / "frontend"
WE = FRONTEND / "js" / "workspace-engine"
UX2 = FRONTEND / "js" / "ux2"

client = TestClient(app)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _js_function(src: str, name: str) -> str:
    marker = f"export function {name}"
    start = src.index(marker)
    paren = src.index("(", start)
    depth = 0
    index = paren
    while index < len(src):
        char = src[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                index += 1
                break
        index += 1
    brace = src.index("{", index)
    depth = 0
    for pos, char in enumerate(src[brace:], start=brace):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return src[start + len("export ") : pos + 1]
    raise AssertionError(f"unclosed function {name}")


def _eval_plan(function_names: list[str], prelude: str, expression: str):
    src = _read(WE / "planning-ops.js")
    names = list(function_names)
    script = "\n".join(_js_function(src, name) for name in names)
    script += f"\n{prelude}\nconsole.log(JSON.stringify({expression}));\n"
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def login(operator: str) -> None:
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text


def test_no_parallel_planning_workspace() -> None:
    html = _read(FRONTEND / "index.html")
    registry = _read(UX2 / "registry.js")
    assert 'id="planningWorkspace"' in html
    assert 'id="planOpsDesk"' in html
    assert 'id="planSbs"' in html
    assert 'id="planEos"' in html
    assert 'id="planMel"' in html
    assert 'id="planGeneratePkg"' not in html
    assert 'id: "planning"' in registry
    assert 'id: "engineering"' in registry
    assert "simulated: true" in registry
    assert "command" in registry


def test_loaders_and_types_planning_objects() -> None:
    loaders = _read(WE / "loaders.js")
    types = _read(WE / "types.js")
    render = _read(WE / "render.js")
    engine = _read(WE / "engine.js")
    ops = _read(FRONTEND / "js" / "planning.js")
    assert "finding: `/planning/deferred-defects/${encodeURIComponent(id)}`" in loaders
    assert "check: `/planning/checks/${encodeURIComponent(id)}`" in loaders
    assert "airworthinessDirective: `/planning/ads/${encodeURIComponent(id)}`" in loaders
    assert "serviceBulletin: `/planning/service-bulletins/${encodeURIComponent(id)}`" in loaders
    assert "engineeringOrder: `/planning/engineering-orders/${encodeURIComponent(id)}`" in loaders
    assert "melItem: `/planning/mel-items/${encodeURIComponent(id)}`" in loaders
    assert "/planning/checks?aircraft_id=" in loaders
    assert "/work-orders/orders?work_package_id=" in loaders
    assert 'type: "check"' in types
    assert 'type: "airworthinessDirective"' in types
    assert "Generate work package" in types
    assert "renderFindingWorkspace" in render
    assert "renderAircraftPlanningBridge" in render
    generic_overview = render.find('\n  if (tabId === "overview")')
    finding_branch = render.find('session.type === "finding"')
    check_branch = render.find('session.type === "check" && tabId === "overview"')
    assert finding_branch > 0
    assert check_branch > 0
    assert generic_overview > finding_branch
    assert generic_overview > check_branch
    assert "bindPlanningOpsPanel" in engine
    assert "planningOpsCacheKeys" in engine
    assert "generateWp" in engine
    assert "runLocked" in ops
    assert "/planning/checks/generate-package" in ops
    assert "planning: refreshPlanningWorkspace" in _read(UX2 / "workspaces.js")


def test_pr8_pr9_pr10_pr11_contracts_still_present() -> None:
    render = _read(WE / "render.js")
    cfg = _read(WE / "configuration.js")
    ops = _read(WE / "maintenance-ops.js")
    log = _read(WE / "logistics-ops.js")
    assert "dueOpenTarget" in render
    assert "deferred_defect" in render
    assert "renderAircraftConfigurationPanel" in cfg or "bindConfigurationPanel" in cfg
    assert "bindMaintenanceOpsPanel" in ops
    assert "bindLogisticsOpsPanel" in log
    html = _read(FRONTEND / "index.html")
    assert 'id="workOrdersWorkspace"' in html
    assert 'id="logisticsWorkspace"' in html
    assert 'id="contextWorkspace"' in html


def test_helper_filter_eligible_and_targets() -> None:
    assert _eval_plan(["eligibleChecks"], "", 'eligibleChecks([{status:"due",id:"1"},{status:"due",id:"2",generated_work_package_id:"wp"}])') == [
        {"status": "due", "id": "1"}
    ]
    filtered = _eval_plan(
        ["filterDueItems"],
        "",
        'filterDueItems([{title:"A check",aircraft_id:"ac-a",urgency:"overdue",source_type:"check"},{title:"B",aircraft_id:"ac-b",urgency:"future",source_type:"ad"}], {aircraftId:"ac-a",urgency:"overdue"})',
    )
    assert len(filtered) == 1
    target = _eval_plan(["dueObjectTarget"], "", 'dueObjectTarget({source_type:"ad",source_id:"ad1",title:"AD-1"})')
    assert target == {"type": "airworthinessDirective", "id": "ad1", "label": "AD-1"}
    assert _eval_plan(["sessionCanManagePlanning", "normalizeRole"], "", 'sessionCanManagePlanning("Viewer")') is False
    assert _eval_plan(["sessionCanManagePlanning", "normalizeRole"], "", 'sessionCanManagePlanning("Operator")') is True
    keys = _eval_plan(
        ["planningOpsCacheKeys"],
        "",
        'planningOpsCacheKeys({type:"finding",id:"d1",record:{aircraft_id:"ac-a",linked_work_order_id:"wo1"}}, {checkId:"c1"})',
    )
    assert "ac-a" in keys["aircraft"]
    assert "wo1" in keys["workOrders"]
    assert "c1" in keys["checks"]


def test_planning_forms_escape_and_inflight() -> None:
    ops = _read(WE / "planning-ops.js")
    desk = _read(FRONTEND / "js" / "planning.js")
    html = _read(FRONTEND / "index.html")
    assert "esc(" in ops
    assert "runLocked" in ops
    assert "window.confirm" in ops
    assert "esc(" in desk
    assert "planOpsDesk" in html
    assert "planStatus" in html


def test_viewer_cannot_manage_planning() -> None:
    login("viewer")
    assert client.get("/api/v1/planning/dashboard").status_code == 200
    assert client.get("/api/v1/planning/due-list").status_code == 200
    denied = client.post(
        "/api/v1/planning/ads",
        json={"ad_number": "AD-VIEWER", "authority": "easa", "title": "blocked"},
    )
    assert denied.status_code == 403
    login("reviewer")
    assert client.get("/api/v1/planning/ads").status_code == 200
    assert (
        client.post(
            "/api/v1/planning/engineering-orders",
            json={"eo_number": "EO-REV", "title": "blocked"},
        ).status_code
        == 403
    )


def test_tenant_isolation_and_get_by_id() -> None:
    login("operator")
    assert client.get("/api/v1/planning/ads", params={"organization_id": "org-aviation-west"}).status_code == 403
    ads = client.get("/api/v1/planning/ads").json()
    assert ads
    fetched = client.get(f"/api/v1/planning/ads/{ads[0]['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == ads[0]["id"]
    missing = client.get("/api/v1/planning/ads/ad-does-not-exist")
    assert missing.status_code == 404
    sbs = client.get("/api/v1/planning/service-bulletins").json()
    if sbs:
        assert client.get(f"/api/v1/planning/service-bulletins/{sbs[0]['id']}").status_code == 200
    checks = client.get("/api/v1/planning/checks", params={"aircraft_id": "ac-c-gmea", "limit": 20}).json()
    assert all(row["aircraft_id"] == "ac-c-gmea" for row in checks)
    if checks:
        one = client.get(f"/api/v1/planning/checks/{checks[0]['id']}")
        assert one.status_code == 200


def test_generate_selected_check_and_409_duplicate() -> None:
    login("operator")
    chk = client.post(
        "/api/v1/planning/checks",
        json={
            "aircraft_id": "ac-c-gmea",
            "program_revision_id": "mpr-a320-line-1",
            "check_code": f"A-UI-{uuid.uuid4().hex[:5].upper()}",
            "check_type": "a",
            "title": "Operator UI generate",
            "interval_calendar_days": 30,
            "bay": "Bay-2",
        },
    )
    assert chk.status_code == 201, chk.text
    check_id = chk.json()["id"]
    detail = client.get(f"/api/v1/planning/checks/{check_id}")
    assert detail.status_code == 200
    gen = client.post(
        "/api/v1/planning/checks/generate-package",
        json={"check_id": check_id, "include_mpd_tasks": True, "max_job_cards": 5},
    )
    assert gen.status_code == 201, gen.text
    assert gen.json()["work_order_ids"]
    again = client.post("/api/v1/planning/checks/generate-package", json={"check_id": check_id})
    assert again.status_code == 409
    wo = client.get(f"/api/v1/work-orders/orders/{gen.json()['work_order_ids'][0]}")
    assert wo.status_code == 200
    assert wo.json()["aircraft_id"] == "ac-c-gmea"


def test_defect_mel_eo_approve_and_hangar() -> None:
    login("operator")
    mel = client.post(
        "/api/v1/planning/mel-items",
        json={
            "list_type": "mel",
            "item_number": f"34-{uuid.uuid4().hex[:3]}",
            "title": "Operator UI MEL",
            "dispatch_category": "C",
            "repair_interval_days": 10,
        },
    )
    assert mel.status_code == 201, mel.text
    mel_id = mel.json()["id"]
    assert client.get(f"/api/v1/planning/mel-items/{mel_id}").status_code == 200
    defect = client.post(
        "/api/v1/planning/deferred-defects",
        json={
            "aircraft_id": "ac-c-gmea",
            "title": "Operator UI defect",
            "deferral_type": "mel",
            "mel_item_id": mel_id,
            "dispatch_category": "C",
        },
    )
    assert defect.status_code == 201, defect.text
    defect_id = defect.json()["id"]
    fetched = client.get(f"/api/v1/planning/deferred-defects/{defect_id}")
    assert fetched.status_code == 200
    assert fetched.json()["aircraft_id"] == "ac-c-gmea"
    listed = client.get("/api/v1/planning/deferred-defects", params={"aircraft_id": "ac-c-gmea"})
    assert any(row["id"] == defect_id for row in listed.json())
    eo = client.post(
        "/api/v1/planning/engineering-orders",
        json={"eo_number": f"EO-UI-{uuid.uuid4().hex[:5].upper()}", "title": "Operator UI EO"},
    )
    assert eo.status_code == 201, eo.text
    eo_id = eo.json()["id"]
    assert client.get(f"/api/v1/planning/engineering-orders/{eo_id}").status_code == 200
    approved = client.post(f"/api/v1/planning/engineering-orders/{eo_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    again = client.post(f"/api/v1/planning/engineering-orders/{eo_id}/approve")
    assert again.status_code == 409
    hangar = client.post(
        "/api/v1/planning/hangar-plans",
        json={"aircraft_id": "ac-c-gmea", "hangar": "Hangar-UI", "bay": "Bay-UI", "shift_code": "day"},
    )
    assert hangar.status_code == 201, hangar.text
    util = client.put(
        "/api/v1/planning/utilization",
        json={"aircraft_id": "ac-c-gmea", "ops_status": "available", "location": "CYUL", "flight_hours": "10"},
    )
    assert util.status_code == 200, util.text


def test_utilization_omitted_counters_are_preserved() -> None:
    login("operator")
    first = client.put(
        "/api/v1/planning/utilization",
        json={
            "aircraft_id": "ac-c-gmea",
            "ops_status": "available",
            "location": "KEEP-HRS",
            "flight_hours": "555.50",
            "flight_cycles": 77,
        },
    )
    assert first.status_code == 200, first.text
    second = client.put(
        "/api/v1/planning/utilization",
        json={"aircraft_id": "ac-c-gmea", "ops_status": "maintenance", "location": "KEEP-HRS-2"},
    )
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["ops_status"] == "maintenance"
    assert body["location"] == "KEEP-HRS-2"
    assert float(body["flight_hours"]) == 555.5
    assert body["flight_cycles"] == 77
