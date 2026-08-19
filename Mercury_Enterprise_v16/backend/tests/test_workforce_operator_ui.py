"""Workforce planning operator UI and HTTP API.

No Playwright. Uses existing workforce_plan_lines + planning RBAC.
GET-by-id is required for Workspace Engine inspect.
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
    script = "\n".join(_js_function(src, name) for name in function_names)
    script += f"\n{prelude}\nconsole.log(JSON.stringify({expression}));\n"
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def login(operator: str) -> None:
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text


def test_workforce_ui_contracts() -> None:
    html = _read(FRONTEND / "index.html")
    desk = _read(FRONTEND / "js" / "planning.js")
    loaders = _read(WE / "loaders.js")
    types = _read(WE / "types.js")
    render = _read(WE / "render.js")
    engine = _read(WE / "engine.js")
    ops = _read(WE / "planning-ops.js")
    assert 'id="planWorkforce"' in html
    assert "SIM / demo data" in html
    assert "/planning/workforce-plan-lines" in desk
    assert "data-plan-action=\"workforce\"" in desk
    assert "runLocked" in desk
    assert "esc(" in desk
    assert "workforcePlanLine: `/planning/workforce-plan-lines/${encodeURIComponent(id)}`" in loaders
    assert 'type: "workforcePlanLine"' in types
    assert "renderWorkforcePlanWorkspace" in render
    assert "renderWorkOrderWorkforce" in render
    generic_overview = render.find('\n  if (tabId === "overview")')
    workforce_branch = render.find('session.type === "workforcePlanLine" && tabId === "overview"')
    assert workforce_branch > 0
    assert generic_overview > workforce_branch
    assert "weWorkforceStatusForm" in ops
    assert "workforcePlanLines" in engine
    assert "bindPlanningOpsPanel" in engine


def test_filter_workforce_and_cache_keys() -> None:
    filtered = _eval_plan(
        ["filterWorkforceLines"],
        "",
        'filterWorkforceLines([{id:"1",work_package_id:"wp-a",role_code:"technician",employee_id:"e1",status:"assigned"},{id:"2",work_package_id:"wp-b",role_code:"aca",employee_id:"e2",status:"planned"}], {workPackageId:"wp-a",roleCode:"technician"})',
    )
    assert len(filtered) == 1
    assert filtered[0]["id"] == "1"
    keys = _eval_plan(
        ["planningOpsCacheKeys"],
        "",
        'planningOpsCacheKeys({type:"workforcePlanLine",id:"wf1",record:{work_package_id:"wp-a"}}, {workforcePlanLineId:"wf2"})',
    )
    assert "wf1" in keys["workforcePlanLines"]
    assert "wf2" in keys["workforcePlanLines"]
    assert _eval_plan(["sessionCanManagePlanning", "normalizeRole"], "", 'sessionCanManagePlanning("Viewer")') is False
    assert _eval_plan(["sessionCanManagePlanning", "normalizeRole"], "", 'sessionCanManagePlanning("Operator")') is True


def test_viewer_reviewer_read_cannot_manage_workforce() -> None:
    login("viewer")
    listed = client.get("/api/v1/planning/workforce-plan-lines")
    assert listed.status_code == 200, listed.text
    denied = client.post(
        "/api/v1/planning/workforce-plan-lines",
        json={"employee_id": "pers-op-east-001", "role_code": "technician", "work_package_id": "wp-demo-c-gmea"},
    )
    assert denied.status_code == 403
    login("reviewer")
    assert client.get("/api/v1/planning/workforce-plan-lines").status_code == 200
    assert (
        client.post(
            "/api/v1/planning/workforce-plan-lines",
            json={"employee_id": "pers-op-east-001", "role_code": "stores", "work_package_id": "wp-demo-c-gmea"},
        ).status_code
        == 403
    )


def test_seeded_demo_lines_and_get_by_id() -> None:
    login("operator")
    listed = client.get("/api/v1/planning/workforce-plan-lines", params={"work_package_id": "wp-demo-c-gmea"})
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert rows, "expected idempotent demo workforce lines on WP-DEMO-001"
    roles = {row["role_code"] for row in rows}
    assert "technician" in roles
    assert "aca" in roles
    assert "ii" in roles
    one = rows[0]
    fetched = client.get(f"/api/v1/planning/workforce-plan-lines/{one['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == one["id"]
    assert fetched.json()["organization_id"] == "org-aviation-east"
    missing = client.get("/api/v1/planning/workforce-plan-lines/wf-does-not-exist")
    assert missing.status_code == 404


def test_create_update_validation_and_tenant_isolation() -> None:
    login("operator")
    created = client.post(
        "/api/v1/planning/workforce-plan-lines",
        json={
            "work_package_id": "wp-demo-c-gmea",
            "employee_id": "pers-op-east-001",
            "role_code": "stores",
            "shift_code": "NIGHT",
            "workload_hours": "1.50",
            "status": "planned",
            "license_ok": True,
            "authorization_ok": False,
            "available": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["role_code"] == "stores"
    assert body["status"] == "planned"
    assert body["license_ok"] is True
    assert body["authorization_ok"] is False
    line_id = body["id"]
    patched = client.patch(
        f"/api/v1/planning/workforce-plan-lines/{line_id}",
        json={"status": "assigned", "shift_code": "DAY", "workload_hours": "2.00", "available": False},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["status"] == "assigned"
    assert patched.json()["shift_code"] == "DAY"
    assert patched.json()["available"] is False
    assert client.post(
        "/api/v1/planning/workforce-plan-lines",
        json={"employee_id": "missing-employee", "role_code": "technician", "work_package_id": "wp-demo-c-gmea"},
    ).status_code == 404
    assert client.post(
        "/api/v1/planning/workforce-plan-lines",
        json={"employee_id": "pers-op-east-001", "role_code": "technician", "work_package_id": "wp-missing"},
    ).status_code == 404
    bad_role = client.post(
        "/api/v1/planning/workforce-plan-lines",
        json={"employee_id": "pers-op-east-001", "role_code": "captain", "work_package_id": "wp-demo-c-gmea"},
    )
    assert bad_role.status_code == 422
    assert client.get("/api/v1/planning/workforce-plan-lines", params={"organization_id": "org-aviation-west"}).status_code == 403


def test_generate_package_creates_workforce_lines() -> None:
    login("operator")
    chk = client.post(
        "/api/v1/planning/checks",
        json={
            "aircraft_id": "ac-c-gmea",
            "program_revision_id": "mpr-a320-line-1",
            "check_code": f"WF-{uuid.uuid4().hex[:5].upper()}",
            "check_type": "a",
            "title": "Workforce generate",
            "interval_calendar_days": 30,
            "shift_code": "DAY",
        },
    )
    assert chk.status_code == 201, chk.text
    gen = client.post(
        "/api/v1/planning/checks/generate-package",
        json={"check_id": chk.json()["id"], "include_mpd_tasks": True, "max_job_cards": 5},
    )
    assert gen.status_code == 201, gen.text
    wp_id = gen.json()["work_package_id"]
    lines = client.get("/api/v1/planning/workforce-plan-lines", params={"work_package_id": wp_id})
    assert lines.status_code == 200, lines.text
    roles = {row["role_code"] for row in lines.json()}
    assert {"technician", "aca", "ii"} <= roles
