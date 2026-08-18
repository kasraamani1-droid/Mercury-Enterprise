"""Enterprise logistics operator UI contracts and live API workflows.

No Playwright. Verifies Logistics Ops / Inventory / Workspace Engine materials
bridge against existing FastAPI logistics routes. Preserves PR #8 DD-1001,
PR #9 configuration UI, and PR #10 maintenance operations.
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


def _eval_log(function_names: list[str], prelude: str, expression: str):
    src = _read(WE / "logistics-ops.js")
    names = list(function_names)
    script = "\n".join(_js_function(src, name) for name in names)
    script += f"\n{prelude}\nconsole.log(JSON.stringify({expression}));\n"
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def login(operator: str) -> None:
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text


def _part_and_location() -> tuple[dict, dict]:
    parts = client.get("/api/v1/logistics/parts").json()
    part = next(row for row in parts if row["oem_part_number"] == "MS21042L3")
    loc = next(row for row in client.get("/api/v1/logistics/locations").json() if row["location_type"] == "general")
    return part, loc


def test_no_parallel_inventory_mutation_workspace() -> None:
    html = _read(FRONTEND / "index.html")
    registry = _read(UX2 / "registry.js")
    assert 'id="logisticsWorkspace"' in html
    assert 'id="inventoryWorkspace"' in html
    assert 'id="jobCardWorkspace"' not in html
    assert 'id="partWorkspace"' not in html
    assert 'id: "logistics"' in registry
    assert 'id: "inventory"' in registry
    assert 'simulated: true' in registry
    assert "command" in registry


def test_loaders_and_types_logistics_objects() -> None:
    loaders = _read(WE / "loaders.js")
    types = _read(WE / "types.js")
    render = _read(WE / "render.js")
    engine = _read(WE / "engine.js")
    ops = _read(FRONTEND / "js" / "logistics.js")
    assert 'part: `/logistics/parts/${encodeURIComponent(id)}`' in loaders
    assert 'materialRequest: `/logistics/material-requests/${encodeURIComponent(id)}`' in loaders
    assert 'purchaseOrder: `/logistics/purchase-orders/${encodeURIComponent(id)}`' in loaders
    assert 'tool: `/logistics/tools/${encodeURIComponent(id)}`' in loaders
    assert "/logistics/material-requests?work_order_id=" in loaders
    assert "/logistics/material-requests?job_card_id=" in loaders
    assert "/logistics/stock/balances?part_master_id=" in loaders
    assert "/logistics/receipts/" in loaders
    assert 'type: "part"' in types
    assert 'type: "materialRequest"' in types
    assert 'id: "materials"' in types
    assert "Request material" in types
    assert "renderWorkOrderMaterials" in render
    assert "renderJobCardMaterials" in render
    assert "renderPartWorkspace" in render
    generic_overview = render.find("\n  if (tabId === \"overview\")")
    part_branch = render.find('session.type === "part" && tabId === "overview"')
    wo_materials = render.find('session.type === "workOrder" && tabId === "materials"')
    assert part_branch > 0
    assert wo_materials > 0
    assert generic_overview > part_branch
    assert generic_overview > wo_materials
    assert "bindLogisticsOpsPanel" in engine
    assert "logisticsOpsCacheKeys" in engine
    assert "requestMaterial" in engine
    assert "/logistics/stock/receive" in ops
    assert "/logistics/scan" in ops
    assert "runLocked" in ops


def test_pr8_pr9_pr10_contracts_still_present() -> None:
    render = _read(WE / "render.js")
    cfg = _read(WE / "configuration.js")
    ops = _read(WE / "maintenance-ops.js")
    assert "dueOpenTarget" in render
    assert "deferred_defect" in render
    assert "finding:" in render
    assert "renderAircraftConfigurationPanel" in render
    assert "bindConfigurationPanel" in cfg
    assert "bindMaintenanceOpsPanel" in ops
    assert "waiting_parts" in ops
    html = _read(FRONTEND / "index.html")
    assert 'id="workOrdersWorkspace"' in html
    assert 'id="contextWorkspace"' in html


def test_helper_qty_filter_scan_rbac_and_cache() -> None:
    assert _eval_log(["parsePositiveQty"], "", "parsePositiveQty('2.5')") == 2.5
    assert _eval_log(["parsePositiveQty"], "", "parsePositiveQty('0')") is None
    assert _eval_log(["parsePositiveQty"], "", "parsePositiveQty('-1')") is None
    avail = _eval_log(["qtyAvailable"], "", "qtyAvailable({qty_on_hand:5,qty_reserved:2})")
    assert avail == 3
    filtered = _eval_log(
        ["filterStockRows"],
        "",
        'filterStockRows([{part_number:"MS1",location_id:"L1",condition:"serviceable"},{part_number:"ZZ",location_id:"L2",condition:"quarantine"}], {q:"ms",locationId:"L1",condition:"serviceable"})',
    )
    assert len(filtered) == 1
    assert filtered[0]["part_number"] == "MS1"
    mrs = _eval_log(
        ["filterMaterialRequests", "mrLinkedTo"],
        "",
        'filterMaterialRequests([{id:"a",job_card_id:"jc1",status:"requested",request_number:"MR-1"},{id:"b",work_order_id:"wo1",status:"issued",request_number:"MR-2"}], {jobCardId:"jc1"})',
    )
    assert [row["id"] for row in mrs] == ["a"]
    assert _eval_log(["transferWarehousesValid"], "", 'transferWarehousesValid("w1","w1")') is False
    assert _eval_log(["transferWarehousesValid"], "", 'transferWarehousesValid("w1","w2")') is True
    scan = _eval_log(
        ["scanTargetObject"],
        "",
        'scanTargetObject({target_type:"part",target_id:"p1",title:"PN"})',
    )
    assert scan == {"type": "part", "id": "p1", "label": "PN"}
    assert _eval_log(["sessionCanStores", "normalizeRole"], "", 'sessionCanStores("Operator")') is True
    assert _eval_log(["sessionCanStores", "normalizeRole"], "", 'sessionCanStores("Viewer")') is False
    assert _eval_log(["sessionCanStores", "normalizeRole"], "", 'sessionCanStores("Reviewer")') is False
    assert _eval_log(["sessionCanTools", "normalizeRole"], "", 'sessionCanTools("Reviewer")') is True
    assert _eval_log(["sessionCanReadLogistics", "normalizeRole"], "", 'sessionCanReadLogistics("Viewer")') is True
    keys = _eval_log(
        ["logisticsOpsCacheKeys"],
        "",
        'logisticsOpsCacheKeys({type:"jobCard",id:"jc1",record:{work_order_id:"wo1",aircraft_id:"ac-a"},bundle:{materialRequests:[{id:"mr1"}]}}, {partId:"p1",materialRequestId:"mr1"})',
    )
    assert "p1" in keys["parts"]
    assert "mr1" in keys["materialRequests"]
    assert "wo1" in keys["workOrders"]
    assert "jc1" in keys["jobCards"]
    mrKeys = _eval_log(
        ["logisticsOpsCacheKeys"],
        "",
        'logisticsOpsCacheKeys({type:"materialRequest",id:"mr1",record:{work_order_id:"wo1",job_card_id:"jc1"},bundle:{jobCard:{aircraft_id:"ac-c-gmea"},workOrder:{aircraft_id:"ac-c-gmea"}}})',
    )
    assert "ac-c-gmea" in mrKeys["aircraft"]
    ops = _read(WE / "logistics-ops.js")
    assert "bundle?.jobCard?.aircraft_id" in ops
    assert "bundle?.workOrder?.aircraft_id" in ops
    conflict = _eval_log(
        ["mutationErrorMessage"],
        "",
        'mutationErrorMessage({status:409,error:"Insufficient available stock: requested 3"})',
    )
    assert conflict.startswith("Conflict:")


def test_logistics_forms_escape_and_inflight() -> None:
    ops = _read(WE / "logistics-ops.js")
    desk = _read(FRONTEND / "js" / "logistics.js")
    html = _read(FRONTEND / "index.html")
    assert "esc(" in ops
    assert "inFlight" in ops
    assert "Request already in progress" in ops
    assert "Conflict:" in ops
    assert "window.confirm" in ops
    assert "esc(" in desk
    assert "logWaitingParts" in html
    assert "logOpsDesk" in html
    assert "homeKpiLowStock" in html
    assert "Barcode / QR / RFID value already in Mercury" in html


def test_viewer_and_reviewer_cannot_mutate_stores() -> None:
    login("viewer")
    assert client.get("/api/v1/logistics/dashboard").status_code == 200
    assert client.get("/api/v1/logistics/stock/balances").status_code == 200
    part, loc = _part_and_location()
    denied = client.post(
        "/api/v1/logistics/stock/receive",
        json={"part_master_id": part["id"], "location_id": loc["id"], "qty": 1, "condition": "serviceable"},
    )
    assert denied.status_code == 403
    login("reviewer")
    assert client.get("/api/v1/logistics/dashboard").status_code == 200
    receive = client.post(
        "/api/v1/logistics/stock/receive",
        json={"part_master_id": part["id"], "location_id": loc["id"], "qty": 1, "condition": "serviceable"},
    )
    assert receive.status_code == 403
    mr = client.post(
        "/api/v1/logistics/material-requests",
        json={"notes": "reviewer-blocked", "lines": [{"part_master_id": part["id"], "qty_requested": 1}]},
    )
    assert mr.status_code == 403


def test_tenant_isolation_and_cross_work_order_filters() -> None:
    login("operator")
    assert client.get("/api/v1/logistics/parts", params={"organization_id": "org-aviation-west"}).status_code == 403
    card = client.get("/api/v1/work-orders/job-cards/jc-demo-oil")
    assert card.status_code == 200
    assert card.json()["aircraft_id"] == "ac-c-gmea"
    other = client.get("/api/v1/work-orders/job-cards", params={"aircraft_id": "ac-c-gmea", "limit": 20})
    assert other.status_code == 200
    assert all(row["aircraft_id"] == "ac-c-gmea" for row in other.json())


def test_job_card_material_request_filter_reserve_issue_and_insufficient_stock() -> None:
    login("operator")
    part, loc = _part_and_location()
    pn = f"LG-{uuid.uuid4().hex[:8].upper()}"
    created_part = client.post(
        "/api/v1/logistics/parts",
        json={"oem_part_number": pn, "description": "Logistics UI part", "part_class": "consumable"},
    )
    assert created_part.status_code == 201, created_part.text
    part_id = created_part.json()["id"]
    recv = client.post(
        "/api/v1/logistics/stock/receive",
        json={"part_master_id": part_id, "location_id": loc["id"], "qty": 2, "condition": "serviceable"},
    )
    assert recv.status_code == 201, recv.text

    card = client.get("/api/v1/work-orders/job-cards/jc-demo-oil").json()
    mr = client.post(
        "/api/v1/logistics/material-requests",
        json={
            "work_order_id": card["work_order_id"],
            "job_card_id": card["id"],
            "notes": "waiting_parts bridge",
            "lines": [{"part_master_id": part_id, "qty_requested": 1}],
        },
    )
    assert mr.status_code == 201, mr.text
    mr_id = mr.json()["id"]
    listed = client.get("/api/v1/logistics/material-requests", params={"job_card_id": card["id"]})
    assert listed.status_code == 200, listed.text
    assert any(row["id"] == mr_id for row in listed.json())
    assert all(row["job_card_id"] == card["id"] for row in listed.json())
    wo_list = client.get("/api/v1/logistics/material-requests", params={"work_order_id": card["work_order_id"]})
    assert any(row["id"] == mr_id for row in wo_list.json())

    assert client.post(f"/api/v1/logistics/material-requests/{mr_id}/approve").status_code == 200
    reserved = client.post(f"/api/v1/logistics/material-requests/{mr_id}/reserve")
    assert reserved.status_code == 200, reserved.text
    issued = client.post(
        f"/api/v1/logistics/material-requests/{mr_id}/issue",
        json={"location_id": loc["id"]},
    )
    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] in {"issued", "reserved"}

    oversell = client.post(
        "/api/v1/logistics/reservations",
        json={"part_master_id": part_id, "qty": 9999, "location_id": loc["id"], "source_type": "manual", "source_id": "test"},
    )
    assert oversell.status_code == 409, oversell.text
    assert "Insufficient" in oversell.json()["detail"] or "stock" in oversell.json()["detail"].lower()

    invalid = client.post(
        "/api/v1/logistics/stock/issue",
        json={"part_master_id": part_id, "qty": 0, "location_id": loc["id"]},
    )
    assert invalid.status_code == 422

    detail = client.get(f"/api/v1/logistics/parts/{part_id}")
    assert detail.status_code == 200
    balances = client.get("/api/v1/logistics/stock/balances", params={"part_master_id": part_id})
    assert balances.status_code == 200
    assert balances.json()


def test_transfer_distinct_warehouse_and_receipt_get() -> None:
    login("operator")
    part, loc = _part_and_location()
    warehouses = client.get("/api/v1/logistics/warehouses").json()
    main = next(row for row in warehouses if row["code"] == "WH-MAIN")
    other = client.post(
        "/api/v1/logistics/warehouses",
        json={"code": f"WH-{uuid.uuid4().hex[:6].upper()}", "name": "Cycle 1 dest", "warehouse_type": "physical"},
    )
    assert other.status_code == 201, other.text
    dest_wh = other.json()
    dest_loc = client.post(
        "/api/v1/logistics/locations",
        json={"warehouse_id": dest_wh["id"], "location_code": f"BIN-{uuid.uuid4().hex[:4].upper()}", "location_type": "general"},
    )
    assert dest_loc.status_code == 201, dest_loc.text
    client.post(
        "/api/v1/logistics/stock/receive",
        json={"part_master_id": part["id"], "location_id": loc["id"], "qty": 1, "condition": "serviceable"},
    )
    same = client.post(
        "/api/v1/logistics/transfers",
        json={
            "from_warehouse_id": main["id"],
            "to_warehouse_id": main["id"],
            "lines": [{"part_master_id": part["id"], "qty": 1}],
        },
    )
    assert same.status_code in {400, 409, 422}
    created = client.post(
        "/api/v1/logistics/transfers",
        json={
            "from_warehouse_id": main["id"],
            "to_warehouse_id": dest_wh["id"],
            "from_location_id": loc["id"],
            "to_location_id": dest_loc.json()["id"],
            "lines": [{"part_master_id": part["id"], "qty": 1}],
        },
    )
    assert created.status_code == 201, created.text
    completed = client.post(
        f"/api/v1/logistics/transfers/{created.json()['id']}/complete",
        json={"to_location_id": dest_loc.json()["id"]},
    )
    assert completed.status_code == 200, completed.text

    vendors = client.get("/api/v1/logistics/vendors").json()
    pr = client.post(
        "/api/v1/logistics/purchase-requests",
        json={"lines": [{"part_master_id": part["id"], "qty": 1}], "notes": "receipt get"},
    )
    assert pr.status_code == 201, pr.text
    pr_id = pr.json()["id"]
    assert client.post(f"/api/v1/logistics/purchase-requests/{pr_id}/approve").status_code == 200
    rfq = client.post(f"/api/v1/logistics/purchase-requests/{pr_id}/rfq")
    assert rfq.status_code == 201, rfq.text
    rfq_id = rfq.json()["id"]
    quote = client.post(
        f"/api/v1/logistics/rfqs/{rfq_id}/quotes",
        json={"vendor_id": vendors[0]["id"], "unit_price": "1.00", "currency": "USD", "lead_time_days": 1},
    )
    assert quote.status_code == 201, quote.text
    select = client.post(f"/api/v1/logistics/rfqs/{rfq_id}/quotes/{quote.json()['id']}/select")
    assert select.status_code == 200, select.text
    po = client.post(f"/api/v1/logistics/rfqs/{rfq_id}/purchase-order", json={})
    assert po.status_code == 201, po.text
    po_id = po.json()["id"]
    po_detail = client.get(f"/api/v1/logistics/purchase-orders/{po_id}")
    assert po_detail.status_code == 200
    line = po_detail.json()["lines"][0]
    receipt = client.post(
        f"/api/v1/logistics/purchase-orders/{po_id}/receive",
        json={"lines": [{"purchase_order_line_id": line["id"], "part_master_id": part["id"], "qty": 1}]},
    )
    assert receipt.status_code == 201, receipt.text
    receipt_id = receipt.json()["id"]
    fetched = client.get(f"/api/v1/logistics/receipts/{receipt_id}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == receipt_id
    assert fetched.json()["lines"]


def test_scan_resolves_seed_barcode() -> None:
    login("operator")
    scan = client.post("/api/v1/logistics/scan", json={"value": "MS21042L3"})
    assert scan.status_code == 200, scan.text
    body = scan.json()
    assert body["resolved"] is True
    assert body["target_type"] in {"part", "stock_unit"}
