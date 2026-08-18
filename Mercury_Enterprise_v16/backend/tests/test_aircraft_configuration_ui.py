"""Aircraft Components & Configuration operator UI — static contract tests.

No Playwright. Verifies Workspace Engine wiring to existing /api/v1/components
routes and that PR #8 finding navigation is preserved. Does not add #componentWorkspace.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PACKAGE_ROOT / "frontend"
WE = FRONTEND / "js" / "workspace-engine"
UX2 = FRONTEND / "js" / "ux2"


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


def _eval_js(function_names: list[str], prelude: str, expression: str):
    src = _read(WE / "configuration.js")
    script = "\n".join(_js_function(src, name) for name in function_names)
    script += f"\n{prelude}\nconsole.log(JSON.stringify({expression}));\n"
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def _eval_resolve(cases: list[list[object]]) -> list[dict[str, object]]:
    return _eval_js(
        ["resolveInstallationHoursCycles"],
        "const cases = " + json.dumps(cases) + ";",
        "cases.map((c) => resolveInstallationHoursCycles(c[0], c[1], c[2]))",
    )


def test_no_parallel_component_workspace() -> None:
    html = _read(FRONTEND / "index.html")
    registry = _read(UX2 / "registry.js")
    assert 'id="componentWorkspace"' not in html
    assert 'id: "components"' not in registry
    assert 'id="aircraftWorkspace"' in html
    assert 'id="contextWorkspace"' in html


def test_loaders_fetch_configuration_and_component_history() -> None:
    loaders = _read(WE / "loaders.js")
    assert "/components/aircraft/" in loaders
    assert "/configuration" in loaders
    assert "/components/serialized" in loaders
    assert "/components/ata-chapters" in loaders
    assert "/components/catalog" in loaders
    assert "/components/serialized/${encodeURIComponent(id)}/history" in loaders
    assert "/auth/session" in loaders
    assert "/fleet/aircraft?limit=100" in loaders
    assert "serializedLoad" in loaders
    assert "hostAircraft" in loaders


def test_configuration_ui_uses_existing_mutate_helpers() -> None:
    api = _read(UX2 / "api.js")
    cfg = _read(WE / "configuration.js")
    engine = _read(WE / "engine.js")
    assert "uxFetchAircraftConfiguration" in api
    assert "/components/serialized/${encodeURIComponent(id)}/install" in api
    assert "/components/serialized/${encodeURIComponent(id)}/remove" in api
    assert "/components/serialized/${encodeURIComponent(id)}/transfer" in api
    assert "uxInstallSerializedComponent" in cfg
    assert "uxRemoveSerializedComponent" in cfg
    assert "uxTransferSerializedComponent" in cfg
    assert "sessionCanManageComponents" in cfg
    assert 'role === "Operator"' in cfg or 'value === "Operator"' in cfg
    assert "refresh: true" in engine
    assert "bindConfigurationPanel" in engine
    assert "tab," in engine or "tab:" in engine


def test_pr8_due_finding_navigation_preserved() -> None:
    render = _read(WE / "render.js")
    assert "dueOpenTarget" in render
    assert "deferred_defect" in render
    assert "finding:" in render
    assert 'tabId === "components"' in render
    assert "Due / findings" in render
    assert "renderAircraftConfigurationPanel" in render
    assert 'session.type === "aircraft"' in render
    assert 'session.type === "digitalTwin"' in render or 'session.type === "digitalTwin"' in render


def test_aircraft_tabs_branch_before_generic_shell() -> None:
    render = _read(WE / "render.js")
    aircraft_idx = render.find('session.type === "aircraft" && (tabId === "configuration" || tabId === "components")')
    twin_idx = render.find('tabId === "configuration" && session.type === "digitalTwin"')
    generic_idx = render.find('tabId === "configuration" || tabId === "components" || tabId === "maintenance"')
    assert aircraft_idx > 0
    assert twin_idx > 0
    assert generic_idx > aircraft_idx
    assert generic_idx > twin_idx


def test_types_expose_install_and_remove_actions() -> None:
    types = _read(WE / "types.js")
    assert 'id: "installComponent"' in types
    assert "Remove from aircraft" in types
    assert 'id: "components"' in types
    assert 'id: "configuration"' in types
    assert 'id: "installHistory"' in types


def test_remove_and_transfer_send_install_snapshot_hours_cycles() -> None:
    cfg = _read(WE / "configuration.js")
    engine = _read(WE / "engine.js")
    assert "resolveInstallationHoursCycles" in cfg
    assert "aircraft_hours_at_install" in cfg
    assert "aircraft_cycles_at_install" in cfg
    assert "uxRemoveSerializedComponent" in cfg
    assert "aircraft_hours: resolved.hours" in cfg
    assert "aircraft_cycles: resolved.cycles" in cfg
    assert cfg.count("aircraft_hours: resolved.hours") >= 2
    assert cfg.count("aircraft_cycles: resolved.cycles") >= 2
    assert 'data-we-cfg-hours="snapshot"' in cfg
    assert 'data-we-cfg-cycles="snapshot"' in cfg
    assert "weCfgRemoveForm" in cfg
    remove_form = cfg.split('id="weCfgRemoveForm"', 1)[1]
    transfer_form = cfg.split('id="weCfgTransferForm"', 1)[1]
    assert 'value="0"' not in remove_form.split("weCfgTransferForm", 1)[0]
    assert 'value="0"' not in transfer_form.split("weCfgRegisterForm", 1)[0]
    assert "resolveInstallationHoursCycles" in engine
    assert "aircraft_hours: resolved.hours" in engine
    assert "aircraft_cycles: resolved.cycles" in engine

    seed = {"aircraft_hours_at_install": "1250.50", "aircraft_cycles_at_install": 840}
    results = _eval_resolve(
        [
            [seed, "", ""],
            [seed, None, None],
            [{}, "", ""],
            [{"aircraft_hours_at_install": None, "aircraft_cycles_at_install": None}, "", ""],
            [seed, "0", "0"],
            [seed, "1300.25", "900"],
            [{"aircraft_hours_at_install": 0, "aircraft_cycles_at_install": 0}, "", ""],
        ]
    )
    assert results[0]["ok"] is True
    assert results[0]["hours"] == 1250.5
    assert results[0]["cycles"] == 840
    assert results[1]["ok"] is True
    assert results[1]["hours"] == 1250.5
    assert results[1]["cycles"] == 840
    assert results[2]["ok"] is False
    assert "not recorded" in str(results[2]["error"]).lower()
    assert results[3]["ok"] is False
    assert results[4]["ok"] is False
    assert "less than installation" in str(results[4]["error"]).lower()
    assert results[5]["ok"] is True
    assert results[5]["hours"] == 1300.25
    assert results[5]["cycles"] == 900
    assert results[6]["ok"] is True
    assert results[6]["hours"] == 0
    assert results[6]["cycles"] == 0


def test_cache_invalidation_covers_component_source_and_transfer_destination() -> None:
    engine = _read(WE / "engine.js")
    cfg = _read(WE / "configuration.js")
    assert "configurationMutationCacheKeys" in engine
    assert "configurationMutationCacheKeys" in cfg
    assert "async function refreshActiveObject(mutation = {})" in engine
    assert "{ refresh: true, tab, label }" in engine
    assert "openGeneration" in engine
    assert "existingTab" in engine
    assert "destinationAircraftId: values.to_status === \"installed\" ? values.to_aircraft_id : \"\"" in cfg
    keys = _eval_js(
        ["configurationMutationCacheKeys"],
        "",
        """configurationMutationCacheKeys(
          { type: "aircraft", id: "ac-a", bundle: { configuration: { installed: [{ component_id: "c-old" }] } } },
          { componentId: "c-new", sourceAircraftId: "ac-a", destinationAircraftId: "ac-b" }
        )""",
    )
    assert "c-new" in keys["components"]
    assert "c-old" in keys["components"]
    assert keys["aircraft"] == ["ac-a", "ac-b"] or set(keys["aircraft"]) == {"ac-a", "ac-b"}


def test_ata_grouping_and_occupied_positions() -> None:
    cfg = _read(WE / "configuration.js")
    loaders = _read(WE / "loaders.js")
    assert "groupRowsByAta" in cfg
    assert "we-cfg-group" in cfg
    assert "occupiedPositions" in cfg
    assert "Position" in cfg and "already occupied" in cfg
    assert "serializedLoad" in loaders
    bundle = {
        "configuration": {
            "installed": [
                {
                    "component_id": "c1",
                    "serial_number": "ENG-SN-1001",
                    "part_number": "CFM56-5B4",
                    "component_type": "engine",
                    "position": "ENG1",
                    "date_installed": "2020-01-01",
                    "tsn_hours": "1250.50",
                    "csn_cycles": 840,
                    "remaining_hours": 10,
                    "remaining_cycles": 5,
                }
            ]
        },
        "serialized": [
            {
                "id": "c1",
                "catalog_item_id": "cat1",
                "component_status": "installed",
                "aircraft_hours_at_install": "1250.50",
                "aircraft_cycles_at_install": 840,
            }
        ],
        "catalog": [{"id": "cat1", "ata_chapter_id": "ata1", "part_number": "CFM56-5B4", "component_type": "engine"}],
        "ataChapters": [{"id": "ata1", "chapter_number": "71", "subchapter": "00", "title": "Power Plant"}],
    }
    joined = _eval_js(
        ["joinAircraftConfiguration"],
        "const bundle = " + json.dumps(bundle) + ";",
        "joinAircraftConfiguration(bundle)",
    )
    assert joined[0]["ata_code"] == "71-00"
    assert joined[0]["ata_title"] == "Power Plant"
    assert joined[0]["serial_number"] == "ENG-SN-1001"
    assert joined[0]["part_number"] == "CFM56-5B4"
    assert joined[0]["position"] == "ENG1"
    groups = _eval_js(
        ["joinAircraftConfiguration", "groupRowsByAta"],
        "const bundle = " + json.dumps(bundle) + ";",
        "groupRowsByAta(joinAircraftConfiguration(bundle))",
    )
    assert groups[0]["label"].startswith("71-00")
    occupied = _eval_js(["occupiedPositions"], "", "occupiedPositions([{position:'eng1'},{position:'ENG1'}])")
    assert occupied == ["ENG1"]


def test_destructive_confirm_and_409_feedback_wired() -> None:
    cfg = _read(WE / "configuration.js")
    assert "destructiveConfirmMessage" in cfg
    assert "window.confirm" in cfg
    assert "mutationErrorMessage" in cfg
    assert "result.status === 409" in cfg
    msg = _eval_js(
        ["destructiveConfirmMessage"],
        "",
        "destructiveConfirmMessage('remove', {serial_number:'ENG-SN-1001', aircraft_label:'C-GMEA', position:'ENG1', destination_status:'stores'})",
    )
    assert "ENG-SN-1001" in msg
    assert "C-GMEA" in msg


def test_pr8_dd1001_finding_chip_contract() -> None:
    render = _read(WE / "render.js")
    planning = _read(PACKAGE_ROOT / "backend" / "app" / "planning" / "service.py")
    assert "dueOpenTarget" in render
    assert "deferred_defect" in render
    assert "finding:" in render
    assert 'defect_number="DD-1001"' in planning or "defect_number=\"DD-1001\"" in planning
    assert "dd-demo-001" in planning


def test_operator_ui_remove_hours_payload_and_409_and_rbac() -> None:
    import uuid

    from fastapi.testclient import TestClient

    from app.main import app
    from conftest import TEST_AUTH_PASSWORD

    client = TestClient(app)

    def login(operator: str) -> None:
        response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
        assert response.status_code == 200

    login("viewer")
    catalog = client.get("/api/v1/components/catalog", params={"component_type": "engine"})
    assert catalog.status_code == 200
    viewer_install = client.post(
        "/api/v1/components/serialized",
        json={"catalog_item_id": catalog.json()[0]["id"], "serial_number": "VIEW-NOPE", "component_status": "stores"},
    )
    assert viewer_install.status_code == 403

    login("operator")
    catalog_id = client.get("/api/v1/components/catalog", params={"component_type": "engine"}).json()[0]["id"]
    suffix = uuid.uuid4().hex[:8].upper()
    created = client.post(
        "/api/v1/components/serialized",
        json={"catalog_item_id": catalog_id, "serial_number": f"UI-{suffix}", "component_status": "stores"},
    )
    assert created.status_code == 201, created.text
    component_id = created.json()["id"]
    login("viewer")
    viewer_mutate = client.post(
        f"/api/v1/components/serialized/{component_id}/install",
        json={
            "aircraft_id": "ac-c-gmea",
            "position": f"UI-{suffix[:4]}",
            "aircraft_hours": "2000.00",
            "aircraft_cycles": 1000,
        },
    )
    assert viewer_mutate.status_code == 403
    login("operator")
    installed = client.post(
        f"/api/v1/components/serialized/{component_id}/install",
        json={
            "aircraft_id": "ac-c-gmea",
            "position": f"UI-{suffix[:4]}",
            "aircraft_hours": "2000.00",
            "aircraft_cycles": 1000,
        },
    )
    assert installed.status_code == 200, installed.text
    bad_hours = client.post(
        f"/api/v1/components/serialized/{component_id}/remove",
        json={"destination_status": "stores", "aircraft_hours": "0", "aircraft_cycles": 0},
    )
    assert bad_hours.status_code == 400
    assert "installation" in str(bad_hours.json().get("detail", "")).lower()
    occupied = client.post(
        "/api/v1/components/serialized",
        json={"catalog_item_id": catalog_id, "serial_number": f"OCC-{suffix}", "component_status": "stores"},
    ).json()["id"]
    conflict = client.post(
        f"/api/v1/components/serialized/{occupied}/install",
        json={
            "aircraft_id": "ac-c-gmea",
            "position": f"UI-{suffix[:4]}",
            "aircraft_hours": "2000.00",
            "aircraft_cycles": 1000,
        },
    )
    assert conflict.status_code == 409
    assert "occupied" in str(conflict.json().get("detail", "")).lower()
    removed = client.post(
        f"/api/v1/components/serialized/{component_id}/remove",
        json={"destination_status": "stores", "aircraft_hours": "2000.00", "aircraft_cycles": 1000},
    )
    assert removed.status_code == 200, removed.text


def test_operator_ui_cross_aircraft_transfer_and_config_isolation() -> None:
    import uuid

    from fastapi.testclient import TestClient

    from app.main import app
    from conftest import TEST_AUTH_PASSWORD

    client = TestClient(app)
    login = client.post("/api/v1/auth/login", json={"operator": "operator", "password": TEST_AUTH_PASSWORD})
    assert login.status_code == 200
    catalog_id = client.get("/api/v1/components/catalog", params={"component_type": "engine"}).json()[0]["id"]
    suffix = uuid.uuid4().hex[:8].upper()
    component_id = client.post(
        "/api/v1/components/serialized",
        json={"catalog_item_id": catalog_id, "serial_number": f"ISO-{suffix}", "component_status": "stores"},
    ).json()["id"]
    assert (
        client.post(
            f"/api/v1/components/serialized/{component_id}/install",
            json={
                "aircraft_id": "ac-c-gmea",
                "position": f"IS-{suffix[:4]}",
                "aircraft_hours": "100.00",
                "aircraft_cycles": 10,
            },
        ).status_code
        == 200
    )
    gmea_before = client.get("/api/v1/components/aircraft/ac-c-gmea/configuration").json()
    gmeb_before = client.get("/api/v1/components/aircraft/ac-c-gmeb/configuration").json()
    assert gmea_before["aircraft_id"] == "ac-c-gmea"
    assert gmeb_before["aircraft_id"] == "ac-c-gmeb"
    assert any(item["component_id"] == component_id for item in gmea_before["installed"])
    assert all(item["component_id"] != component_id for item in gmeb_before["installed"])
    transferred = client.post(
        f"/api/v1/components/serialized/{component_id}/transfer",
        json={
            "to_status": "installed",
            "to_aircraft_id": "ac-c-gmeb",
            "position": f"IB-{suffix[:4]}",
            "aircraft_hours": "100.00",
            "aircraft_cycles": 10,
            "reason": "ui_cross_aircraft",
        },
    )
    assert transferred.status_code == 200, transferred.text
    assert transferred.json()["current_aircraft_id"] == "ac-c-gmeb"
    gmea_after = client.get("/api/v1/components/aircraft/ac-c-gmea/configuration").json()
    gmeb_after = client.get("/api/v1/components/aircraft/ac-c-gmeb/configuration").json()
    assert all(item["component_id"] != component_id for item in gmea_after["installed"])
    assert any(item["component_id"] == component_id for item in gmeb_after["installed"])
    seed = client.get("/api/v1/components/aircraft/ac-c-gmea/configuration").json()
    assert any(item["serial_number"] == "ENG-SN-1001" for item in seed["installed"])
