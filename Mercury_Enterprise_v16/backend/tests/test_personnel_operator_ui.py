"""Personnel qualifications / stamps operator UI contracts and live API workflows.

No Playwright. Verifies Personnel desk / Workspace Engine employee objects
against existing FastAPI personnel routes. Preserves PR #8–#12 operator UI.
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


def _eval_pers(function_names: list[str], prelude: str, expression: str):
    src = _read(WE / "personnel-ops.js")
    names = list(function_names)
    script = "\n".join(_js_function(src, name) for name in names)
    script += f"\n{prelude}\nconsole.log(JSON.stringify({expression}));\n"
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def login(operator: str) -> None:
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text


def _employee(number: str) -> dict:
    rows = client.get("/api/v1/personnel/employees").json()
    return next(row for row in rows if row["employee_number"] == number)


def test_no_parallel_personnel_workspace() -> None:
    html = _read(FRONTEND / "index.html")
    registry = _read(UX2 / "registry.js")
    assert 'id="personnelWorkspace"' in html
    assert 'id="persOpsDesk"' in html
    assert 'id="persEmployees"' in html
    assert 'id="persAlerts"' in html
    assert 'id="persStamps"' in html
    assert 'id="persDashKpis"' in html
    assert 'id: "personnel"' in registry
    assert "Personnel" in registry
    assert "simulated: true" in registry


def test_loaders_and_types_employee_objects() -> None:
    loaders = _read(WE / "loaders.js")
    types = _read(WE / "types.js")
    render = _read(WE / "render.js")
    engine = _read(WE / "engine.js")
    ops = _read(WE / "personnel-ops.js")
    router = _read(PACKAGE_ROOT / "backend" / "app" / "personnel" / "router.py")
    assert "employee: `/personnel/employees/${encodeURIComponent(id)}`" in loaders
    assert "/personnel/employees/${encodeURIComponent(id)}/stamps" in loaders
    assert 'type: "employee"' in types
    assert "renderEmployeeWorkspace" in render
    assert "renderJobCardPersonnelBridge" in render
    generic_overview = render.find('\n  if (tabId === "overview")')
    emp_branch = render.find('session.type === "employee" && tabId === "overview"')
    assert emp_branch > 0
    assert generic_overview > emp_branch
    assert "bindPersonnelOpsPanel" in engine
    assert "personnelOpsCacheKeys" in engine
    assert "openPersonnel" in engine
    assert "runLocked" in ops
    assert '@router.get("/employees/{employee_id}/stamps"' in router
    get_pos = router.index('@router.get("/employees/{employee_id}/stamps"')
    post_pos = router.index('@router.post("/employees/{employee_id}/stamps"')
    assert get_pos < post_pos
    assert "personnel: refreshPersonnelWorkspace" in _read(UX2 / "workspaces.js")


def test_pr8_through_pr12_contracts_still_present() -> None:
    html = _read(FRONTEND / "index.html")
    render = _read(WE / "render.js")
    assert 'id="workOrdersWorkspace"' in html
    assert 'id="logisticsWorkspace"' in html
    assert 'id="planningWorkspace"' in html
    assert 'id="techLibraryWorkspace"' in html
    assert "dueOpenTarget" in render
    assert "renderJobCardMaterialsBridge" in render


def test_helper_filter_alerts_and_roles() -> None:
    filtered = _eval_pers(
        ["filterEmployees"],
        "",
        'filterEmployees([{full_name:"Demo AME",employee_number:"E-1001",status:"active",id:"e1"},{full_name:"Other",employee_number:"E-9",status:"inactive",id:"e2"}], {q:"ame",status:"active"})',
    )
    assert len(filtered) == 1
    assert filtered[0]["id"] == "e1"
    now = 1_700_000_000_000
    assert _eval_pers(["qualificationAlert"], "", f'qualificationAlert({{expires_at:"2010-01-01T00:00:00Z"}},{now})') == "expired"
    assert _eval_pers(["qualificationAlert"], "", f'qualificationAlert({{expires_at:new Date({now + 5 * 86400000}).toISOString()}},{now})') == "expiring"
    assert _eval_pers(["qualificationAlert"], "", f'qualificationAlert({{expires_at:new Date({now + 90 * 86400000}).toISOString()}},{now})') == "ok"
    assert _eval_pers(["qualificationAlert"], "", "qualificationAlert({})") == "none"
    assert _eval_pers(["sessionCanManagePersonnel", "normalizeRole"], "", 'sessionCanManagePersonnel("Viewer")') is False
    assert _eval_pers(["sessionCanManagePersonnel", "normalizeRole"], "", 'sessionCanManagePersonnel("Operator")') is True
    keys = _eval_pers(
        ["personnelOpsCacheKeys"],
        "",
        'personnelOpsCacheKeys({type:"employee",id:"e1"}, {jobCardId:"jc1"})',
    )
    assert "e1" in keys["employees"]
    assert "jc1" in keys["jobCards"]


def test_personnel_forms_escape_and_inflight() -> None:
    ops = _read(WE / "personnel-ops.js")
    desk = _read(FRONTEND / "js" / "personnel.js")
    html = _read(FRONTEND / "index.html")
    assert "esc(" in ops
    assert "runLocked" in ops
    assert "does not invent retirement" in ops
    assert "esc(" in desk
    assert "persOpsDesk" in html
    assert "renderJobCardPersonnelBridge" in _read(WE / "render.js")


def test_viewer_cannot_manage_personnel() -> None:
    login("viewer")
    assert client.get("/api/v1/personnel/employees").status_code == 200
    emp = _employee("E-1001")
    assert client.get(f"/api/v1/personnel/employees/{emp['id']}").status_code == 200
    stamps = client.get(f"/api/v1/personnel/employees/{emp['id']}/stamps")
    assert stamps.status_code == 200
    assert any(row["stamp_code"] == "2468" for row in stamps.json())
    assert (
        client.post(
            "/api/v1/personnel/employees",
            json={"employee_number": "NOPE-V", "full_name": "blocked"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/personnel/employees/{emp['id']}/qualifications",
            json={"qualification_type": "training", "code": "NOPE"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/personnel/employees/{emp['id']}/stamps",
            json={"stamp_code": "9999"},
        ).status_code
        == 403
    )
    login("reviewer")
    assert client.get(f"/api/v1/personnel/employees/{emp['id']}/stamps").status_code == 200
    assert (
        client.post(
            f"/api/v1/personnel/employees/{emp['id']}/authorizations",
            json={"auth_type": "stamp", "scope": "blocked"},
        ).status_code
        == 403
    )


def test_tenant_isolation_and_get_by_id() -> None:
    login("operator")
    assert client.get("/api/v1/personnel/employees", params={"organization_id": "org-aviation-west"}).status_code == 403
    emp = _employee("E-1001")
    fetched = client.get(f"/api/v1/personnel/employees/{emp['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["employee_number"] == "E-1001"
    missing = client.get("/api/v1/personnel/employees/emp-does-not-exist")
    assert missing.status_code == 404
    aca = _employee("E-2001")
    quals = client.get(f"/api/v1/personnel/employees/{aca['id']}/qualifications")
    assert quals.status_code == 200
    tech_quals = client.get(f"/api/v1/personnel/employees/{emp['id']}/qualifications").json()
    assert not any(row.get("qualification_type") == "aca" for row in tech_quals)


def test_operator_create_employee_qualification_and_stamp() -> None:
    login("operator")
    suffix = uuid.uuid4().hex[:6].upper()
    number = f"E-UI-{suffix}"
    created = client.post(
        "/api/v1/personnel/employees",
        json={
            "employee_number": number,
            "full_name": "Operator UI Employee",
            "position_title": "AME",
            "email": f"ui-{suffix}@example.invalid",
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]
    dup = client.post(
        "/api/v1/personnel/employees",
        json={"employee_number": number, "full_name": "Duplicate"},
    )
    assert dup.status_code == 409
    assert client.get(f"/api/v1/personnel/employees/{emp_id}").status_code == 200
    qual = client.post(
        f"/api/v1/personnel/employees/{emp_id}/qualifications",
        json={"qualification_type": "training", "code": f"TR-{suffix}", "authority": "internal"},
    )
    assert qual.status_code == 201, qual.text
    auth = client.post(
        f"/api/v1/personnel/employees/{emp_id}/authorizations",
        json={"auth_type": "independent_inspection", "scope": "ATA 71"},
    )
    assert auth.status_code == 201, auth.text
    stamp = client.post(
        f"/api/v1/personnel/employees/{emp_id}/stamps",
        json={"stamp_code": f"ST-{suffix}", "label": "UI stamp"},
    )
    assert stamp.status_code == 201, stamp.text
    listed = client.get(f"/api/v1/personnel/employees/{emp_id}/stamps")
    assert listed.status_code == 200
    assert any(row["stamp_code"] == f"ST-{suffix}" for row in listed.json())
    again = client.post(
        f"/api/v1/personnel/employees/{emp_id}/stamps",
        json={"stamp_code": f"ST2-{suffix}", "label": "Second profile"},
    )
    assert again.status_code == 201, again.text
    stamps = client.get(f"/api/v1/personnel/employees/{emp_id}/stamps").json()
    assert len(stamps) >= 2
