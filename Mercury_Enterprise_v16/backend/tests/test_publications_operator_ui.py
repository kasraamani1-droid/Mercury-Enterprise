"""Publications / Technical Library operator UI contracts and live API workflows.

No Playwright. Verifies library desk / Workspace Engine publication objects
against existing FastAPI publications and library routes. Preserves PR #8–#12.
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


def _eval_pub(function_names: list[str], prelude: str, expression: str):
    src = _read(WE / "publications-ops.js")
    names = list(function_names)
    script = "\n".join(_js_function(src, name) for name in names)
    script += f"\n{prelude}\nconsole.log(JSON.stringify({expression}));\n"
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def login(operator: str) -> None:
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text


def test_no_parallel_library_workspace() -> None:
    html = _read(FRONTEND / "index.html")
    registry = _read(UX2 / "registry.js")
    assert 'id="techLibraryWorkspace"' in html
    assert 'id="libOpsDesk"' in html
    assert 'id="libBrowse"' in html
    assert 'id="libPublications"' in html
    assert 'id="libSearchResults"' in html
    assert 'id="libAds"' in html
    assert 'id="libSbs"' in html
    assert 'id="libEos"' in html
    assert 'id="libStatus"' in html
    assert 'id="libDashKpis"' in html
    assert 'id="techLibraryBoard"' not in html
    assert 'id: "techLibrary"' in registry
    assert 'id: "personnel"' in registry
    assert "simulated: true" in registry
    assert "command" in registry


def test_loaders_and_types_publication_objects() -> None:
    loaders = _read(WE / "loaders.js")
    types = _read(WE / "types.js")
    render = _read(WE / "render.js")
    engine = _read(WE / "engine.js")
    ops = _read(WE / "publications-ops.js")
    desk = _read(FRONTEND / "js" / "library.js")
    assert "publication: `/publications/${encodeURIComponent(id)}`" in loaders
    assert "/publications/by-aircraft/" in loaders
    assert "/publications/by-component/" in loaders
    assert "/publications/${encodeURIComponent(id)}/revisions" in loaders
    assert 'type: "publication"' in types
    assert 'id: "publications"' in types
    assert "renderPublicationWorkspace" in render
    assert "renderAircraftPublications" in render
    assert "renderLinkedPublication" in render
    generic_overview = render.find('\n  if (tabId === "overview")')
    pub_branch = render.find('session.type === "publication" && tabId === "overview"')
    assert pub_branch > 0
    assert generic_overview > pub_branch
    assert "bindPublicationsOpsPanel" in engine
    assert "publicationsOpsCacheKeys" in engine
    assert "openLibrary" in engine
    assert "runLocked" in ops
    assert "activate: false" in ops
    assert "/publications" in desk
    assert "techLibrary: refreshTechLibraryWorkspace" in _read(UX2 / "workspaces.js")


def test_pr8_through_pr12_contracts_still_present() -> None:
    render = _read(WE / "render.js")
    cfg = _read(WE / "configuration.js")
    ops = _read(WE / "maintenance-ops.js")
    log = _read(WE / "logistics-ops.js")
    plan = _read(WE / "planning-ops.js")
    assert "dueOpenTarget" in render
    assert "deferred_defect" in render
    assert "bindConfigurationPanel" in cfg
    assert "bindMaintenanceOpsPanel" in ops
    assert "bindLogisticsOpsPanel" in log
    assert "bindPlanningOpsPanel" in plan
    html = _read(FRONTEND / "index.html")
    assert 'id="workOrdersWorkspace"' in html
    assert 'id="logisticsWorkspace"' in html
    assert 'id="planningWorkspace"' in html
    assert 'id="planOpsDesk"' in html
    assert 'id="contextWorkspace"' in html


def test_helper_filter_browse_and_roles() -> None:
    filtered = _eval_pub(
        ["filterPublications"],
        "",
        'filterPublications([{title:"AMM A320",publication_number:"AMM-1",publication_code:"AMM",status:"active",id:"p1"},{title:"CMM",publication_number:"CMM-1",publication_code:"CMM",status:"active",id:"p2"}], {q:"amm",code:"AMM"})',
    )
    assert len(filtered) == 1
    assert filtered[0]["id"] == "p1"
    assert _eval_pub(["libraryBrowseQuery"], "", 'libraryBrowseQuery({manufacturerId:"mfr-airbus",modelId:"model-a320"})') == (
        "/library/browse?manufacturer_id=mfr-airbus&aircraft_model_id=model-a320"
    )
    assert _eval_pub(["sessionCanManagePublications", "normalizeRole"], "", 'sessionCanManagePublications("Viewer")') is False
    assert _eval_pub(["sessionCanManagePublications", "normalizeRole"], "", 'sessionCanManagePublications("Operator")') is True
    assert _eval_pub(["sessionCanAdminPublications", "normalizeRole"], "", 'sessionCanAdminPublications("Operator")') is False
    assert _eval_pub(["sessionCanAdminPublications", "normalizeRole"], "", 'sessionCanAdminPublications("Administrator")') is True
    keys = _eval_pub(
        ["publicationsOpsCacheKeys"],
        "",
        'publicationsOpsCacheKeys({type:"publication",id:"p1",record:{aircraft_id:"ac-a"}}, {adId:"ad1",componentId:"c1"})',
    )
    assert "p1" in keys["publications"]
    assert "ad1" in keys["ads"]
    assert "c1" in keys["components"]


def test_publication_forms_escape_and_inflight() -> None:
    ops = _read(WE / "publications-ops.js")
    desk = _read(FRONTEND / "js" / "library.js")
    html = _read(FRONTEND / "index.html")
    assert "esc(" in ops
    assert "runLocked" in ops
    assert "window.confirm" in ops
    assert "esc(" in desk
    assert "libOpsDesk" in html
    assert "libStatus" in html


def test_viewer_cannot_manage_publications() -> None:
    login("viewer")
    assert client.get("/api/v1/publications/types").status_code == 200
    assert client.get("/api/v1/library/browse").status_code == 200
    denied = client.post(
        "/api/v1/publications",
        json={"publication_type_code": "AMM", "title": "blocked", "publication_number": "NOPE-VIEWER"},
    )
    assert denied.status_code == 403
    login("reviewer")
    assert client.get("/api/v1/publications").status_code == 200
    assert (
        client.post(
            "/api/v1/publications",
            json={"publication_type_code": "SB", "title": "blocked", "publication_number": "NOPE-REV"},
        ).status_code
        == 403
    )


def test_operator_cannot_admin_archive_access_or_activate() -> None:
    login("operator")
    suffix = uuid.uuid4().hex[:8].upper()
    created = client.post(
        "/api/v1/publications",
        json={
            "publication_type_code": "SB",
            "title": f"UI SB {suffix}",
            "publication_number": f"SB-UI-{suffix}",
            "revision_number": "Rev 01",
            "activate_revision": True,
            "storage": {"kind": "none"},
        },
    )
    assert created.status_code == 201, created.text
    pub_id = created.json()["id"]
    assert client.post(f"/api/v1/publications/{pub_id}/archive").status_code == 403
    assert (
        client.post(
            f"/api/v1/publications/{pub_id}/access-classification",
            json={"access_classification": "restricted"},
        ).status_code
        == 403
    )
    draft = client.post(
        f"/api/v1/publications/{pub_id}/revisions",
        json={"revision_number": "Rev 02", "activate": False, "storage": {"kind": "none"}},
    )
    assert draft.status_code == 201, draft.text
    assert (
        client.post(
            f"/api/v1/publications/{pub_id}/revisions",
            json={"revision_number": "Rev 03", "activate": True, "storage": {"kind": "none"}},
        ).status_code
        == 403
    )
    assert client.post(f"/api/v1/publications/{pub_id}/revisions/{draft.json()['id']}/activate").status_code == 403


def test_tenant_isolation_get_by_id_and_fleet_links() -> None:
    login("operator")
    assert client.get("/api/v1/publications", params={"organization_id": "org-aviation-west"}).status_code == 403
    pubs = client.get("/api/v1/publications", params={"publication_code": "AMM"}).json()
    assert pubs
    fetched = client.get(f"/api/v1/publications/{pubs[0]['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == pubs[0]["id"]
    missing = client.get("/api/v1/publications/pub-does-not-exist")
    assert missing.status_code == 404
    by_aircraft = client.get("/api/v1/publications/by-aircraft/ac-c-gmea")
    assert by_aircraft.status_code == 200
    assert by_aircraft.json()
    browse = client.get("/api/v1/library/browse", params={"manufacturer_id": "mfr-airbus", "aircraft_model_id": "model-a320"})
    assert browse.status_code == 200
    assert browse.json()["nodes"]


def test_create_draft_duplicate_and_admin_activate() -> None:
    login("operator")
    suffix = uuid.uuid4().hex[:8].upper()
    number = f"SB-OP-{suffix}"
    created = client.post(
        "/api/v1/publications",
        json={
            "publication_type_code": "SB",
            "title": f"Operator UI {suffix}",
            "publication_number": number,
            "manufacturer_id": "mfr-airbus",
            "aircraft_model_id": "model-a320",
            "ata_chapter_id": "ata-71-00",
            "revision_number": "Rev 01",
            "activate_revision": True,
            "storage": {"kind": "external_url", "uri": "https://example.invalid/sb/ui"},
            "access_classification": "internal",
        },
    )
    assert created.status_code == 201, created.text
    pub_id = created.json()["id"]
    dup = client.post(
        "/api/v1/publications",
        json={"publication_type_code": "SB", "title": "dup", "publication_number": number},
    )
    assert dup.status_code == 409
    detail = client.get(f"/api/v1/publications/{pub_id}")
    assert detail.status_code == 200
    draft = client.post(
        f"/api/v1/publications/{pub_id}/revisions",
        json={"revision_number": "Rev 02", "activate": False, "change_summary": "UI draft", "storage": {"kind": "none"}},
    )
    assert draft.status_code == 201, draft.text
    again = client.post(
        f"/api/v1/publications/{pub_id}/revisions",
        json={"revision_number": "Rev 02", "activate": False, "storage": {"kind": "none"}},
    )
    assert again.status_code == 409
    login("admin")
    activated = client.post(f"/api/v1/publications/{pub_id}/revisions/{draft.json()['id']}/activate")
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "current"
    pub = client.get(f"/api/v1/publications/{pub_id}").json()
    assert pub["current_revision_number"] == "Rev 02"
    ata = client.post(f"/api/v1/publications/{pub_id}/ata/ata-71-00")
    assert ata.status_code in {200, 201, 409}
