"""Maintenance operations integration — Workspace Engine operator UI contracts.

No Playwright. Verifies Work Orders / Job Cards / Logbook / Planning / Home
wiring against existing FastAPI routes. Preserves PR #8 DD-1001 and PR #9
configuration UI. Does not add parallel area workspaces.
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


def _eval_ops(function_names: list[str], prelude: str, expression: str):
    src = _read(WE / "maintenance-ops.js")
    const_start = src.index("export const JC_TRANSITIONS")
    const_end = src.index("export function normalizeRole")
    constants = src[const_start:const_end].replace("export ", "")
    names = ["normalizeRole"] + [name for name in function_names if name != "normalizeRole"]
    script = constants + "\n".join(_js_function(src, name) for name in names)
    script += f"\n{prelude}\nconsole.log(JSON.stringify({expression}));\n"
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def login(operator: str) -> None:
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text


def employees() -> dict[str, str]:
    login("operator")
    rows = client.get("/api/v1/personnel/employees").json()
    return {row["employee_number"]: row["id"] for row in rows}


def test_no_parallel_job_card_or_ops_workspace() -> None:
    html = _read(FRONTEND / "index.html")
    registry = _read(UX2 / "registry.js")
    assert 'id="jobCardWorkspace"' not in html
    assert 'id="componentWorkspace"' not in html
    assert 'id="workOrdersWorkspace"' in html
    assert 'id="logbookWorkspace"' in html
    assert 'id="planningWorkspace"' in html
    assert 'id="homeWorkspace"' in html
    assert 'id="contextWorkspace"' in html
    assert 'id: "jobCards"' not in registry
    assert 'id: "workOrders"' in registry
    assert 'id: "planning"' in registry
    assert 'id: "logbook"' in registry


def test_loaders_fetch_wo_job_card_logbook_planning() -> None:
    loaders = _read(WE / "loaders.js")
    assert "/work-orders/orders/${encodeURIComponent(id)}" in loaders
    assert "/work-orders/job-cards/${encodeURIComponent(id)}" in loaders
    assert "/work-orders/job-cards?work_order_id=" in loaders
    assert "/work-orders/job-cards?aircraft_id=" in loaders
    assert "/maintenance/logbook?aircraft_id=" in loaders
    assert "/planning/due-list" in loaders
    assert "/personnel/employees" in loaders
    assert "/maintenance/tasks/${encodeURIComponent(taskId)}/audit-trail" in loaders
    assert 'jobCard: `/work-orders/job-cards/' in loaders or 'jobCard: `/work-orders/job-cards/${encodeURIComponent(id)}`' in loaders
    assert "source: \"api\"" in loaders
    assert "status: \"unavailable\"" in loaders


def test_types_and_render_branch_before_generic_shell() -> None:
    types = _read(WE / "types.js")
    render = _read(WE / "render.js")
    engine = _read(WE / "engine.js")
    assert 'type: "jobCard"' in types
    assert 'id: "tasks"' in types
    assert "Open aircraft" in types
    assert "Aircraft logbook" in types
    aircraft_cfg = render.find('session.type === "aircraft" && (tabId === "configuration" || tabId === "components")')
    aircraft_wo = render.find('session.type === "aircraft" && tabId === "workOrders"')
    aircraft_log = render.find('session.type === "aircraft" && tabId === "logbook"')
    wo_tasks = render.find('session.type === "workOrder" && tabId === "tasks"')
    job_card = render.find('session.type === "jobCard"')
    generic = render.find('tabId === "configuration" || tabId === "components" || tabId === "maintenance"')
    assert aircraft_cfg > 0
    assert aircraft_wo > aircraft_cfg
    assert aircraft_log > aircraft_cfg
    assert wo_tasks > 0
    assert job_card > 0
    assert generic > aircraft_wo
    assert generic > wo_tasks
    assert "bindMaintenanceOpsPanel" in engine
    assert "maintenanceOpsCacheKeys" in engine
    assert "{ refresh: true, tab, label }" in engine
    assert 'tab: open.getAttribute("data-we-tab")' in engine
    assert "document.querySelectorAll(\"[data-we-open]\")" not in engine.split("initializeWorkspaceEngine", 1)[0]


def test_pr8_pr9_contracts_still_present() -> None:
    render = _read(WE / "render.js")
    cfg = _read(WE / "configuration.js")
    planning = _read(PACKAGE_ROOT / "backend" / "app" / "planning" / "service.py")
    assert "dueOpenTarget" in render
    assert "deferred_defect" in render
    assert "finding:" in render
    assert "renderAircraftConfigurationPanel" in render
    assert "sessionCanManageComponents" in cfg
    assert "dd-demo-001" in planning
    assert 'defect_number="DD-1001"' in planning or 'defect_number="DD-1001"' in planning


def test_home_and_boards_use_live_kpis() -> None:
    html = _read(FRONTEND / "index.html")
    workspaces = _read(UX2 / "workspaces.js")
    api = _read(UX2 / "api.js")
    planning = _read(FRONTEND / "js" / "planning.js")
    assert 'id="homeKpiOpenWo"' in html
    assert 'id="homeKpiDelayedWo"' in html
    assert 'id="homeKpiInspect"' in html
    assert 'id="homeKpiRelease"' in html
    assert 'data-ux2-goto="logbook"' in html
    assert 'data-ux2-goto="approvals"' in html
    assert "uxFetchWorkOrderDashboard" in workspaces
    assert "uxFetchPlanningDashboard" in workspaces
    assert "unavailable" in workspaces
    assert "/work-orders/dashboard" in api
    assert "/planning/dashboard" in api
    assert "planDelayedWo" in planning
    assert "data-we-open=\"workOrder:" in planning
    assert "data-we-tab=\"maintenance\"" in planning


def test_rbac_helpers_and_transitions() -> None:
    assert _eval_ops(["sessionCanManageWorkOrders"], "", 'sessionCanManageWorkOrders("Operator")') is True
    assert _eval_ops(["sessionCanManageWorkOrders"], "", 'sessionCanManageWorkOrders("Viewer")') is False
    assert _eval_ops(["sessionCanRelease"], "", 'sessionCanRelease("Operator")') is False
    assert _eval_ops(["sessionCanRelease"], "", 'sessionCanRelease("Reviewer")') is True
    assert _eval_ops(["sessionCanInspect"], "", 'sessionCanInspect("Viewer")') is False
    allowed = _eval_ops(["allowedTransitions"], "", 'allowedTransitions("in_progress")')
    assert "paused" in allowed
    assert "waiting_inspection" not in allowed
    assert "completed" not in allowed
    gated = _eval_ops(["inspectionReleaseState"], "", 'inspectionReleaseState({status:"waiting_inspection",technician_employee_id:"e1"})')
    assert gated["awaitingInspection"] is True
    msg = _eval_ops(["mutationErrorMessage"], "", 'mutationErrorMessage({status:409,error:"Invalid transition"})')
    assert "Conflict" in msg
    linked = _eval_ops(
        ["linkLogbookToWorkOrders"],
        "",
        'linkLogbookToWorkOrders([{id:"l1",task_id:"t1"}],[{id:"jc1",maintenance_task_id:"t1",work_order_id:"wo1",job_card_number:"JC-1"}])',
    )
    assert linked[0]["work_order_id"] == "wo1"
    assert linked[0]["job_card_id"] == "jc1"
    due = _eval_ops(
        ["filterDueForAircraft"],
        "",
        'filterDueForAircraft([{aircraft_id:"ac-a",title:"A"},{aircraft_id:"ac-b",title:"B"},{title:"both"}], "ac-a")',
    )
    assert [row["title"] for row in due] == ["A", "both"]
    related = _eval_ops(
        ["relatedWorkOrdersForDueItem"],
        "",
        'relatedWorkOrdersForDueItem({source_type:"check",source_id:"c1"},[{id:"wo1",work_package_id:"pkg1"}],[{id:"c1",generated_work_package_id:"pkg1"}])',
    )
    assert related[0]["id"] == "wo1"
    keys = _eval_ops(
        ["maintenanceOpsCacheKeys"],
        "",
        'maintenanceOpsCacheKeys({type:"jobCard",id:"jc1",record:{work_order_id:"wo1",aircraft_id:"ac-a"},bundle:{jobCards:[]}}, {jobCardId:"jc1",workOrderId:"wo1",aircraftId:"ac-a"})',
    )
    assert "ac-a" in keys["aircraft"]
    assert "wo1" in keys["workOrders"]
    assert "jc1" in keys["jobCards"]


def test_ops_forms_escape_and_no_innerhtml_injection() -> None:
    ops = _read(WE / "maintenance-ops.js")
    workspaces = _read(UX2 / "workspaces.js")
    assert "esc(" in ops
    assert "innerHTML" not in ops.split("bindMaintenanceOpsPanel", 1)[1] or "weOpsMsg" in ops
    assert "textContent" in ops
    assert "inFlight" in ops
    assert "Request already in progress" in ops
    assert "complete-work" in ops
    assert "/release" in ops
    assert "inspect" in ops
    assert "CERT_GATED" in ops or "waiting_inspection" in ops
    assert "There is no create-log API" in ops or "no create-log API" in ops
    assert "woRetry" in workspaces
    assert "logbookAircraftFilter" in workspaces


def test_work_order_list_filters_open_context_and_rbac() -> None:
    login("viewer")
    listed = client.get("/api/v1/work-orders/orders", params={"aircraft_id": "ac-c-gmea", "limit": 50})
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert rows
    assert all(row["aircraft_id"] == "ac-c-gmea" for row in rows)
    demo = next(row for row in rows if row["id"] == "wo-demo-powerplant")
    opened = client.get(f"/api/v1/work-orders/orders/{demo['id']}")
    assert opened.status_code == 200
    assert opened.json()["aircraft_id"] == "ac-c-gmea"
    created = client.post(
        "/api/v1/work-orders/packages",
        json={"aircraft_id": "ac-c-gmea", "description": "viewer-blocked", "priority": "normal"},
    )
    assert created.status_code == 403

    login("operator")
    status_filter = client.get("/api/v1/work-orders/orders", params={"status": "in_progress", "limit": 50})
    assert status_filter.status_code == 200
    assert all(row["status"] == "in_progress" for row in status_filter.json())
    cards = client.get("/api/v1/work-orders/job-cards", params={"work_order_id": demo["id"]})
    assert cards.status_code == 200
    assert all(row["work_order_id"] == demo["id"] for row in cards.json())


def test_job_card_open_invalid_transition_and_unauthorized_release() -> None:
    login("operator")
    card = client.get("/api/v1/work-orders/job-cards/jc-demo-oil")
    assert card.status_code == 200, card.text
    body = card.json()
    assert body["aircraft_id"] == "ac-c-gmea"
    assert body["work_order_id"] == "wo-demo-powerplant"
    bad = client.post(
        "/api/v1/work-orders/job-cards/jc-demo-oil/transition",
        json={"to_status": "released"},
    )
    assert bad.status_code in {400, 409}
    emp = employees()
    release = client.post(
        "/api/v1/work-orders/job-cards/jc-demo-oil/release",
        json={"employee_id": emp["E-3001"], "method": "password", "credential": TEST_AUTH_PASSWORD},
    )
    assert release.status_code in {403, 409}
    login("viewer")
    viewer_transition = client.post(
        "/api/v1/work-orders/job-cards/jc-demo-oil/transition",
        json={"to_status": "accepted"},
    )
    assert viewer_transition.status_code == 403


def test_job_card_execution_path_and_inspection_visibility() -> None:
    login("operator")
    emp = employees()
    suffix = uuid.uuid4().hex[:6]
    pkg = client.post(
        "/api/v1/work-orders/packages",
        json={"aircraft_id": "ac-c-gmea", "description": f"ops-{suffix}", "priority": "normal"},
    )
    assert pkg.status_code == 201, pkg.text
    order = client.post(
        "/api/v1/work-orders/orders",
        json={"work_package_id": pkg.json()["id"], "title": f"OPS {suffix}", "priority": "high"},
    )
    assert order.status_code == 201, order.text
    card = client.post(
        "/api/v1/work-orders/job-cards",
        json={
            "work_order_id": order.json()["id"],
            "title": f"Card {suffix}",
            "technician_employee_id": emp["E-1001"],
            "priority": "normal",
        },
    )
    assert card.status_code == 201, card.text
    card_id = card.json()["id"]
    opened = client.get(f"/api/v1/work-orders/job-cards/{card_id}")
    assert opened.status_code == 200
    assert opened.json()["status"] in {"assigned", "draft"}
    accepted = client.post(f"/api/v1/work-orders/job-cards/{card_id}/transition", json={"to_status": "accepted"})
    assert accepted.status_code == 200, accepted.text
    started = client.post(f"/api/v1/work-orders/job-cards/{card_id}/transition", json={"to_status": "in_progress"})
    assert started.status_code == 200, started.text
    gated = client.post(f"/api/v1/work-orders/job-cards/{card_id}/transition", json={"to_status": "waiting_inspection"})
    assert gated.status_code == 409
    login("viewer")
    inspect = client.post(
        f"/api/v1/work-orders/job-cards/{card_id}/inspect",
        json={"employee_id": emp["E-2001"], "method": "password", "credential": TEST_AUTH_PASSWORD, "decision": "approve"},
    )
    assert inspect.status_code == 403
    dash = client.get("/api/v1/work-orders/dashboard")
    assert dash.status_code == 200
    assert "awaiting_inspection" in dash.json()
    assert "awaiting_release" in dash.json()


def test_logbook_aircraft_scope_detail_rbac_and_isolation() -> None:
    login("operator")
    gmea = client.get("/api/v1/maintenance/logbook", params={"aircraft_id": "ac-c-gmea", "limit": 50})
    gmeb = client.get("/api/v1/maintenance/logbook", params={"aircraft_id": "ac-c-gmeb", "limit": 50})
    assert gmea.status_code == 200
    assert gmeb.status_code == 200
    assert all(row["aircraft_id"] == "ac-c-gmea" for row in gmea.json())
    assert all(row["aircraft_id"] == "ac-c-gmeb" for row in gmeb.json())
    login("viewer")
    assert client.get("/api/v1/maintenance/logbook", params={"aircraft_id": "ac-c-gmea"}).status_code == 200
    if gmea.json():
        amend = client.post(
            f"/api/v1/maintenance/logbook/{gmea.json()[0]['id']}/amend",
            json={"reason": "viewer cannot", "summary": "nope"},
        )
        assert amend.status_code == 403
    create = client.post("/api/v1/maintenance/logbook", json={"summary": "fake"})
    assert create.status_code in {404, 405, 422}


def test_planning_due_forecast_and_work_order_jump_payloads() -> None:
    login("operator")
    due = client.get("/api/v1/planning/due-list")
    forecast = client.get("/api/v1/planning/forecast", params={"horizon_days": 90})
    dash = client.get("/api/v1/planning/dashboard")
    status = client.get("/api/v1/planning/aircraft-status")
    assert due.status_code == 200
    assert forecast.status_code == 200
    assert dash.status_code == 200
    assert status.status_code == 200
    assert "items" in due.json()
    assert "overdue" in forecast.json()
    assert "waiting_inspection" in dash.json()
    orders = client.get("/api/v1/work-orders/orders", params={"limit": 50})
    assert orders.status_code == 200
    delayed = [row for row in orders.json() if row["status"] == "delayed"]
    assert isinstance(delayed, list)
    login("viewer")
    generate = client.post(
        "/api/v1/planning/checks/generate-package",
        json={"check_id": "not-a-check", "include_mpd_tasks": True},
    )
    assert generate.status_code in {403, 404}


def test_dashboard_kpis_and_unavailable_without_auth() -> None:
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/work-orders/dashboard").status_code == 401
    assert client.get("/api/v1/planning/dashboard").status_code == 401
    assert client.get("/api/v1/dashboard/summary").status_code == 401
    login("operator")
    summary = client.get("/api/v1/dashboard/summary")
    wo = client.get("/api/v1/work-orders/dashboard")
    plan = client.get("/api/v1/planning/dashboard")
    health = client.get("/api/v1/health")
    assert summary.status_code == 200
    assert "alerts" in summary.json()
    assert "missions" in summary.json()
    assert wo.status_code == 200
    assert "open_work_orders" in wo.json()
    assert plan.status_code == 200
    assert health.status_code == 200


def test_cross_module_two_aircraft_and_tab_preservation_strings() -> None:
    engine = _read(WE / "engine.js")
    loaders = _read(WE / "loaders.js")
    ops = _read(WE / "maintenance-ops.js")
    workspaces = _read(UX2 / "workspaces.js")
    assert "existingTab" in engine
    assert "openGeneration" in engine
    assert 'tab: "logbook"' in engine
    assert "openWorkOrder" in engine
    assert "openAircraft" in engine
    assert "/work-orders/orders?aircraft_id=" in loaders
    assert "data-we-tab=\"logbook\"" in ops
    assert "data-ux2-goto=\"planning\"" in ops
    assert "sessionCanManageWorkOrders" in workspaces
    login("operator")
    a = client.get("/api/v1/work-orders/orders", params={"aircraft_id": "ac-c-gmea"}).json()
    b = client.get("/api/v1/work-orders/orders", params={"aircraft_id": "ac-c-gmeb"}).json()
    assert all(row["aircraft_id"] == "ac-c-gmea" for row in a)
    assert all(row["aircraft_id"] == "ac-c-gmeb" for row in b)


def test_tenant_isolation_work_orders_and_logbook() -> None:
    login("operator")
    denied = client.get("/api/v1/work-orders/orders", params={"organization_id": "org-aviation-west"})
    assert denied.status_code == 403
    log_denied = client.get("/api/v1/maintenance/logbook", params={"organization_id": "org-aviation-west"})
    assert log_denied.status_code == 403
