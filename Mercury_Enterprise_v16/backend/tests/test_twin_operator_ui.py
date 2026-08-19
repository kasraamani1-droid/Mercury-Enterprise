"""Digital Twin operator UI contracts and live API workflows.

No Playwright. Verifies Digital Twin desk / Workspace Engine twin objects
against existing FastAPI /api/v1/twin routes. Preserves PR #8–#13.
Workforce HTTP CRUD is not invented — those APIs do not exist yet.
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


def _eval_twin(function_names: list[str], prelude: str, expression: str):
    src = _read(WE / "twin-ops.js")
    names = list(function_names)
    script = "\n".join(_js_function(src, name) for name in names)
    script += f"\n{prelude}\nconsole.log(JSON.stringify({expression}));\n"
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def login(operator: str) -> None:
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text


def test_no_parallel_twin_workspace() -> None:
    html = _read(FRONTEND / "index.html")
    registry = _read(UX2 / "registry.js")
    assert 'id="assetTwinWorkspace"' in html
    assert 'id="twinOpsDesk"' in html
    assert 'id="twinStatus"' in html
    assert 'id="twinDashKpis"' in html
    assert 'id="twinSearchResults"' in html
    assert 'id="assetTwinList"' in html
    assert 'id="assetTwinStage"' in html
    assert 'id="twinWorkspace"' not in html
    assert 'id: "assetTwin"' in registry
    assert "simulated: true" in registry
    assert "digitalTwin" in registry


def test_loaders_and_types_twin_objects() -> None:
    loaders = _read(WE / "loaders.js")
    types = _read(WE / "types.js")
    render = _read(WE / "render.js")
    engine = _read(WE / "engine.js")
    ops = _read(WE / "twin-ops.js")
    desk = _read(FRONTEND / "js" / "twin.js")
    assert "digitalTwin: `/twin/twins/${encodeURIComponent(id)}`" in loaders
    assert "/twin/twins/by-uuid/" in loaders
    assert "/twin/twins/${encodeURIComponent(twinId)}/passport" in loaders
    assert "/twin/search?q=" in loaders
    assert "hydrateTwinDetails" in loaders
    assert "matchTwinToEntity" in loaders
    assert 'type: "digitalTwin"' in types
    assert 'id: "passport"' in types
    assert "openLinkedAsset" in types
    assert "display_name" in types
    assert "renderTwinOverview" in render
    assert "renderHostTwinPanel" in render
    generic_overview = render.find('\n  if (tabId === "overview")')
    twin_branch = render.find('session.type === "digitalTwin" && tabId === "overview"')
    assert twin_branch > 0
    assert generic_overview > twin_branch
    assert 'tabId === "configuration" && session.type === "digitalTwin"' in render
    assert "bindTwinOpsPanel" in engine
    assert "twinOpsCacheKeys" in engine
    assert "lifecycle_state: defaultLifecycleForType" in engine
    assert "in_service" not in engine
    assert "runLocked" in ops
    assert "esc(" in ops
    assert "window.confirm" in ops
    assert "/twin/twins" in desk
    assert "assetTwin: refreshAssetTwinWorkspace" in _read(UX2 / "workspaces.js")
    assert "initializeTwin" in _read(FRONTEND / "js" / "app.js")


def test_pr8_through_pr13_contracts_still_present() -> None:
    render = _read(WE / "render.js")
    cfg = _read(WE / "configuration.js")
    ops = _read(WE / "maintenance-ops.js")
    log = _read(WE / "logistics-ops.js")
    plan = _read(WE / "planning-ops.js")
    pubs = _read(WE / "publications-ops.js")
    pers = _read(WE / "personnel-ops.js")
    assert "dueOpenTarget" in render
    assert "deferred_defect" in render
    assert "bindConfigurationPanel" in cfg
    assert "bindMaintenanceOpsPanel" in ops
    assert "bindLogisticsOpsPanel" in log
    assert "bindPlanningOpsPanel" in plan
    assert "bindPublicationsOpsPanel" in pubs
    assert "bindPersonnelOpsPanel" in pers
    html = _read(FRONTEND / "index.html")
    assert 'id="workOrdersWorkspace"' in html
    assert 'id="logisticsWorkspace"' in html
    assert 'id="planningWorkspace"' in html
    assert 'id="planOpsDesk"' in html
    assert 'id="techLibraryWorkspace"' in html
    assert 'id="personnelWorkspace"' in html
    assert 'id="contextWorkspace"' in html
    planning = _read(FRONTEND / "js" / "planning.js")
    assert 'name="publication_id"' in planning
    assert "body.publication_id" in planning


def test_helper_filter_bind_and_roles() -> None:
    filtered = _eval_twin(
        ["filterTwins"],
        "",
        'filterTwins([{display_name:"C-GMEA Twin",twin_type:"aircraft",lifecycle_state:"operated",id:"t1",serial_number:"GMEA"},{display_name:"Torque",twin_type:"tool",lifecycle_state:"delivered",id:"t2"}], {q:"gmea",twinType:"aircraft"})',
    )
    assert len(filtered) == 1
    assert filtered[0]["id"] == "t1"
    search = _eval_twin(["twinSearchQuery"], "", 'twinSearchQuery({q:"FYXZ",twinType:"aircraft"})')
    assert search.startswith("/twin/search?")
    assert "q=FYXZ" in search
    assert "twin_type=aircraft" in search
    assert "limit=40" in search
    hit = _eval_twin(
        ["matchTwinToEntity"],
        "",
        'matchTwinToEntity([{id:"t1",fabric_entity_id:"ac-c-gmea",fabric_entity_type:"aircraft"},{id:"t2",fabric_entity_id:"ac-c-gmea",fabric_entity_type:"tool"}], {entityId:"ac-c-gmea",entityType:"aircraft"})',
    )
    assert hit["id"] == "t1"
    assert _eval_twin(["defaultLifecycleForType"], "", 'defaultLifecycleForType("aircraft")') == "operated"
    assert _eval_twin(["defaultLifecycleForType"], "", 'defaultLifecycleForType("tool")') == "delivered"
    assert _eval_twin(["isTerminalLifecycle"], "", 'isTerminalLifecycle("retired")') is True
    assert _eval_twin(["isTerminalLifecycle"], "", 'isTerminalLifecycle("operated")') is False
    assert _eval_twin(["bindTwinType"], "", 'bindTwinType("component")') == "serialized_component"
    assert _eval_twin(["bindFabricEntityType"], "", 'bindFabricEntityType("aircraft")') == "aircraft"
    assert _eval_twin(
        ["linkedAssetTarget"],
        "",
        'linkedAssetTarget({fabric_entity_type:"serialized_component",fabric_entity_id:"sc-1"})',
    ) == {"type": "component", "id": "sc-1", "label": "sc-1"}
    rel = _eval_twin(
        ["twinRelationshipRows"],
        "",
        'twinRelationshipRows({twin_id:"t1",fabric_relationships:[{relationship_type:"installed_on"}]})',
    )
    assert rel[0]["relationship_type"] == "installed_on"
    assert _eval_twin(["sessionCanManageTwins", "normalizeRole"], "", 'sessionCanManageTwins("Viewer")') is False
    assert _eval_twin(["sessionCanManageTwins", "normalizeRole"], "", 'sessionCanManageTwins("Reviewer")') is False
    assert _eval_twin(["sessionCanManageTwins", "normalizeRole"], "", 'sessionCanManageTwins("Operator")') is True
    assert _eval_twin(["sessionCanReadTwins", "normalizeRole"], "", 'sessionCanReadTwins("Viewer")') is True
    keys = _eval_twin(
        ["twinOpsCacheKeys", "linkedAssetTarget"],
        "",
        'twinOpsCacheKeys({type:"digitalTwin",id:"t1",record:{fabric_entity_type:"aircraft",fabric_entity_id:"ac-c-gmea"}}, {twinId:"t2"})',
    )
    assert "t1" in keys["twins"]
    assert "t2" in keys["twins"]
    assert "ac-c-gmea" in keys["aircraft"]


def test_twin_forms_escape_and_inflight() -> None:
    ops = _read(WE / "twin-ops.js")
    desk = _read(FRONTEND / "js" / "twin.js")
    html = _read(FRONTEND / "index.html")
    assert "esc(" in ops
    assert "runLocked" in ops
    assert "esc(" in desk
    assert "twinOpsDesk" in html
    assert "twinStatus" in html
    assert "refreshGeneration" in desk


def test_viewer_and_reviewer_cannot_manage_twins() -> None:
    login("viewer")
    assert client.get("/api/v1/twin/overview").status_code == 200
    assert client.get("/api/v1/twin/twins").status_code == 200
    denied = client.post(
        "/api/v1/twin/twins",
        json={"twin_type": "tool", "display_name": "blocked", "serial_number": "NOPE-VIEWER"},
    )
    assert denied.status_code == 403
    login("reviewer")
    assert client.get("/api/v1/twin/twins").status_code == 200
    assert (
        client.post(
            "/api/v1/twin/twins",
            json={"twin_type": "tool", "display_name": "blocked", "serial_number": "NOPE-REV"},
        ).status_code
        == 403
    )


def test_tenant_isolation_get_by_id_and_uuid() -> None:
    login("operator")
    assert client.get("/api/v1/twin/twins", params={"organization_id": "org-aviation-west"}).status_code == 403
    twins = client.get("/api/v1/twin/twins", params={"twin_type": "aircraft"}).json()
    assert twins
    twin = twins[0]
    fetched = client.get(f"/api/v1/twin/twins/{twin['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == twin["id"]
    assert fetched.json()["twin_uuid"]
    by_uuid = client.get(f"/api/v1/twin/twins/by-uuid/{twin['twin_uuid']}")
    assert by_uuid.status_code == 200, by_uuid.text
    assert by_uuid.json()["id"] == twin["id"]
    missing = client.get("/api/v1/twin/twins/twin-does-not-exist")
    assert missing.status_code == 404
    passport = client.get(f"/api/v1/twin/twins/{twin['id']}/passport")
    assert passport.status_code == 200
    assert passport.json()["never_disappears"] is True
    fleet = client.get("/api/v1/fleet/aircraft/ac-c-gmea")
    assert fleet.status_code == 200, fleet.text


def test_operator_create_lifecycle_history_config_reliability() -> None:
    login("operator")
    suffix = uuid.uuid4().hex[:8].upper()
    created = client.post(
        "/api/v1/twin/twins",
        json={
            "twin_type": "aircraft",
            "display_name": f"C-GMEA operator twin {suffix}",
            "serial_number": f"GMEA-{suffix}",
            "part_number": "A320-DEMO",
            "fabric_entity_type": "aircraft",
            "fabric_entity_id": "ac-c-gmea",
            "lifecycle_state": "operated",
            "ensure_passport": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    twin_id = body["id"]
    assert body["lifecycle_state"] == "operated"
    assert body["fabric_entity_id"] == "ac-c-gmea"
    assert body["twin_uuid"]
    invalid = client.post(
        f"/api/v1/twin/twins/{twin_id}/lifecycle",
        json={"to_state": "in_service", "summary": "invalid vocab"},
    )
    assert invalid.status_code == 400
    life = client.post(
        f"/api/v1/twin/twins/{twin_id}/lifecycle",
        json={"to_state": "inspected", "summary": "Operator inspection", "related_ref": "WO-UI"},
    )
    assert life.status_code == 200, life.text
    assert life.json()["lifecycle_state"] == "inspected"
    hist = client.post(
        f"/api/v1/twin/twins/{twin_id}/history",
        json={"history_kind": "inspection", "title": "UI inspection", "summary": "Passed", "related_ref": "WO-UI"},
    )
    assert hist.status_code == 201, hist.text
    cfg = client.post(
        f"/api/v1/twin/twins/{twin_id}/configurations",
        json={"baseline": "current", "version_label": f"CFG-{suffix}", "configuration_json": "{}", "set_as_current": True},
    )
    assert cfg.status_code == 201, cfg.text
    rel = client.post(
        f"/api/v1/twin/twins/{twin_id}/reliability",
        json={"metric_code": "mtbur", "metric_value": "1200", "unit": "hours", "window_label": "rolling_12m"},
    )
    assert rel.status_code == 201, rel.text
    assert rel.json()["architecture_only"] == "true"
    edges = client.get(f"/api/v1/twin/twins/{twin_id}/relationships")
    assert edges.status_code == 200
    assert "digital_thread_hint" in edges.json()
    dup = client.post(
        "/api/v1/twin/twins",
        json={
            "twin_type": "aircraft",
            "display_name": "dup",
            "serial_number": f"GMEA-{suffix}",
            "part_number": "A320-DEMO",
        },
    )
    assert dup.status_code == 409


def test_planning_ad_create_accepts_existing_publication_id() -> None:
    login("operator")
    pubs = client.get("/api/v1/publications", params={"publication_code": "AMM"}).json()
    assert pubs
    pub_id = pubs[0]["id"]
    suffix = uuid.uuid4().hex[:8].upper()
    created = client.post(
        "/api/v1/planning/ads",
        json={
            "ad_number": f"AD-UI-{suffix}",
            "authority": "easa",
            "title": f"Operator AD {suffix}",
            "mandatory": True,
            "publication_id": pub_id,
        },
    )
    assert created.status_code in {200, 201}, created.text
    assert created.json()["publication_id"] == pub_id
