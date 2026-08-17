"""Program B — Enterprise Logistics API and workflow tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    r = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert r.status_code == 200
    return r.json()


def test_seed_warehouse_parts_tools_vendor():
    login_as("operator")
    warehouses = client.get("/api/v1/logistics/warehouses").json()
    assert any(w["code"] == "WH-MAIN" for w in warehouses)
    parts = client.get("/api/v1/logistics/parts").json()
    assert any(p["oem_part_number"] == "MS21042L3" for p in parts)
    tools = client.get("/api/v1/logistics/tools").json()
    assert len(tools) >= 1
    vendors = client.get("/api/v1/logistics/vendors").json()
    assert len(vendors) >= 1


def test_viewer_can_read_not_manage():
    login_as("viewer")
    assert client.get("/api/v1/logistics/dashboard").status_code == 200
    assert (
        client.post(
            "/api/v1/logistics/warehouses",
            json={"code": "X", "name": "Nope"},
        ).status_code
        == 403
    )


def test_tenant_isolation_logistics():
    login_as("operator")
    assert client.get("/api/v1/logistics/parts", params={"organization_id": "org-aviation-west"}).status_code == 403


def test_dashboard_and_shortages():
    login_as("operator")
    dash = client.get("/api/v1/logistics/dashboard").json()
    assert dash["parts"] >= 1
    assert "low_stock_parts" in dash
    shortages = client.get("/api/v1/logistics/shortages").json()
    assert "items" in shortages


def test_part_master_create_and_identifier_scan():
    login_as("operator")
    pn = f"PN-{uuid.uuid4().hex[:8].upper()}"
    created = client.post(
        "/api/v1/logistics/parts",
        json={
            "oem_part_number": pn,
            "description": "Test consumable",
            "part_class": "consumable",
            "issue_policy": "FEFO",
            "min_stock": 5,
            "reorder_point": 10,
            "max_stock": 100,
        },
    )
    assert created.status_code == 201, created.text
    part_id = created.json()["id"]
    code = f"BC-{uuid.uuid4().hex[:10].upper()}"
    ident = client.post(
        "/api/v1/logistics/identifiers",
        json={"part_master_id": part_id, "identifier_type": "barcode", "value": code},
    )
    assert ident.status_code == 201, ident.text
    scan = client.post("/api/v1/logistics/scan", json={"value": code})
    assert scan.status_code == 200, scan.text
    body = scan.json()
    assert body["resolved"] is True
    assert body["target_type"] == "part"
    assert body["target_id"] == part_id


def test_receive_issue_fifo_and_movements_audited():
    login_as("operator")
    parts = client.get("/api/v1/logistics/parts").json()
    part = next(p for p in parts if p["oem_part_number"] == "MS21042L3")
    locations = client.get("/api/v1/logistics/locations").json()
    loc = next(l for l in locations if l["location_type"] == "general")
    recv = client.post(
        "/api/v1/logistics/stock/receive",
        json={
            "part_master_id": part["id"],
            "location_id": loc["id"],
            "qty": 5,
            "batch_number": f"B-{uuid.uuid4().hex[:6]}",
            "condition": "serviceable",
        },
    )
    assert recv.status_code == 201, recv.text
    issue = client.post(
        "/api/v1/logistics/stock/issue",
        json={"part_master_id": part["id"], "qty": 1, "location_id": loc["id"]},
    )
    assert issue.status_code == 200, issue.text
    movements = client.get("/api/v1/logistics/stock/movements", params={"limit": 20}).json()
    assert any(m["movement_type"] in {"receive", "issue"} for m in movements)


def test_fefo_prefers_earlier_expiry():
    login_as("operator")
    pn = f"FEFO-{uuid.uuid4().hex[:6].upper()}"
    part = client.post(
        "/api/v1/logistics/parts",
        json={
            "oem_part_number": pn,
            "description": "FEFO sealant",
            "part_class": "consumable",
            "issue_policy": "FEFO",
            "shelf_life_days": 90,
        },
    ).json()
    loc = next(l for l in client.get("/api/v1/logistics/locations").json() if l["location_type"] == "general")
    later = (datetime.utcnow() + timedelta(days=60)).isoformat()
    sooner = (datetime.utcnow() + timedelta(days=10)).isoformat()
    client.post(
        "/api/v1/logistics/stock/receive",
        json={
            "part_master_id": part["id"],
            "location_id": loc["id"],
            "qty": 2,
            "lot_number": "LATER",
            "expires_at": later,
        },
    )
    early = client.post(
        "/api/v1/logistics/stock/receive",
        json={
            "part_master_id": part["id"],
            "location_id": loc["id"],
            "qty": 2,
            "lot_number": "SOON",
            "expires_at": sooner,
        },
    )
    assert early.status_code == 201, early.text
    issued = client.post(
        "/api/v1/logistics/stock/issue",
        json={"part_master_id": part["id"], "qty": 1, "location_id": loc["id"]},
    )
    assert issued.status_code == 200, issued.text
    units = client.get(
        "/api/v1/logistics/stock/units",
        params={"part_master_id": part["id"]},
    ).json()
    soon_unit = next(u for u in units if u["lot_number"] == "SOON")
    assert float(soon_unit["qty"]) < 2


def test_reservation_prevents_oversell():
    login_as("operator")
    pn = f"RSV-{uuid.uuid4().hex[:6].upper()}"
    part = client.post(
        "/api/v1/logistics/parts",
        json={"oem_part_number": pn, "description": "Reserve test", "part_class": "consumable"},
    ).json()
    loc = next(l for l in client.get("/api/v1/logistics/locations").json() if l["location_type"] == "general")
    client.post(
        "/api/v1/logistics/stock/receive",
        json={"part_master_id": part["id"], "location_id": loc["id"], "qty": 2},
    )
    r1 = client.post(
        "/api/v1/logistics/reservations",
        json={"part_master_id": part["id"], "qty": 2, "location_id": loc["id"]},
    )
    assert r1.status_code == 201, r1.text
    r2 = client.post(
        "/api/v1/logistics/reservations",
        json={"part_master_id": part["id"], "qty": 1, "location_id": loc["id"]},
    )
    assert r2.status_code in (400, 409), r2.text


def test_material_request_workflow():
    login_as("operator")
    parts = client.get("/api/v1/logistics/parts").json()
    part = next(p for p in parts if p["oem_part_number"] == "MS21042L3")
    created = client.post(
        "/api/v1/logistics/material-requests",
        json={
            "notes": "Hangar need",
            "lines": [{"part_master_id": part["id"], "qty_requested": 1}],
        },
    )
    assert created.status_code == 201, created.text
    mr_id = created.json()["id"]
    assert client.post(f"/api/v1/logistics/material-requests/{mr_id}/approve").status_code == 200
    assert client.post(f"/api/v1/logistics/material-requests/{mr_id}/reserve").status_code == 200
    issued = client.post(f"/api/v1/logistics/material-requests/{mr_id}/issue", json={})
    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] in {"issued", "reserved", "approved"}


def test_purchase_flow_partial_receive():
    login_as("operator")
    parts = client.get("/api/v1/logistics/parts").json()
    part = next(p for p in parts if p["oem_part_number"] == "MS21042L3")
    vendors = client.get("/api/v1/logistics/vendors").json()
    vendor_id = vendors[0]["id"]
    pr = client.post(
        "/api/v1/logistics/purchase-requests",
        json={"lines": [{"part_master_id": part["id"], "qty": 4}], "notes": "restock"},
    )
    assert pr.status_code == 201, pr.text
    pr_id = pr.json()["id"]
    assert client.post(f"/api/v1/logistics/purchase-requests/{pr_id}/approve").status_code == 200
    rfq = client.post(f"/api/v1/logistics/purchase-requests/{pr_id}/rfq")
    assert rfq.status_code == 201, rfq.text
    rfq_id = rfq.json()["id"]
    quote = client.post(
        f"/api/v1/logistics/rfqs/{rfq_id}/quotes",
        json={"vendor_id": vendor_id, "unit_price": "12.50", "currency": "USD", "lead_time_days": 7},
    )
    assert quote.status_code == 201, quote.text
    quote_id = quote.json()["id"]
    assert client.post(f"/api/v1/logistics/rfqs/{rfq_id}/quotes/{quote_id}/select").status_code == 200
    po = client.post(f"/api/v1/logistics/rfqs/{rfq_id}/purchase-order", json={})
    assert po.status_code == 201, po.text
    po_id = po.json()["id"]
    loc = next(l for l in client.get("/api/v1/logistics/locations").json() if l["location_type"] == "receiving")
    receipt = client.post(
        f"/api/v1/logistics/purchase-orders/{po_id}/receive",
        json={
            "location_id": loc["id"],
            "lines": [{"purchase_order_line_id": po.json()["lines"][0]["id"], "qty": 2}],
        },
    )
    assert receipt.status_code == 201, receipt.text
    receipt_body = receipt.json()
    receipt_id = receipt_body["id"]
    inspect_lines = [{"line_id": line["id"], "accept": True} for line in receipt_body["lines"]]
    assert client.post(
        f"/api/v1/logistics/receipts/{receipt_id}/inspect",
        json={"lines": inspect_lines},
    ).status_code == 200
    putaway_loc = next(l for l in client.get("/api/v1/logistics/locations").json() if l["location_type"] == "general")
    put = client.post(
        f"/api/v1/logistics/receipts/{receipt_id}/putaway",
        json={"location_id": putaway_loc["id"]},
    )
    assert put.status_code == 200, put.text
    po_after = client.get(f"/api/v1/logistics/purchase-orders/{po_id}").json()
    assert po_after["status"] in {"partial", "open", "received"}


def test_tool_calibration_gate_and_issue():
    login_as("operator")
    tools = client.get("/api/v1/logistics/tools").json()
    assert tools
    tool = next((t for t in tools if t["status"] == "available"), None)
    if tool is None:
        created = client.post(
            "/api/v1/logistics/tools",
            json={"tool_code": f"TL-T-{uuid.uuid4().hex[:6].upper()}", "description": "Test tool", "calibration_required": True},
        )
        assert created.status_code == 201, created.text
        tool = created.json()
    tool_id = tool["id"]
    cal = client.post(
        f"/api/v1/logistics/tools/{tool_id}/calibrate",
        json={
            "due_at": (datetime.utcnow() + timedelta(days=180)).isoformat(),
            "certificate_number": f"CAL-{uuid.uuid4().hex[:6]}",
        },
    )
    assert cal.status_code == 201, cal.text
    issued = client.post(
        f"/api/v1/logistics/tools/{tool_id}/issue",
        json={"issued_to": "tech.one"},
    )
    assert issued.status_code in (200, 201), issued.text
    returned = client.post(f"/api/v1/logistics/tools/{tool_id}/return")
    assert returned.status_code == 200, returned.text


def test_rotable_cycle_open_close():
    login_as("operator")
    parts = client.get("/api/v1/logistics/parts").json()
    rotable = next((p for p in parts if p["part_class"] == "rotable"), None)
    assert rotable is not None
    units = client.get("/api/v1/logistics/stock/units", params={"part_master_id": rotable["id"]}).json()
    if not units:
        loc = next(l for l in client.get("/api/v1/logistics/locations").json() if l["location_type"] == "general")
        recv = client.post(
            "/api/v1/logistics/stock/receive",
            json={
                "part_master_id": rotable["id"],
                "location_id": loc["id"],
                "qty": 1,
                "serial_number": f"SN-{uuid.uuid4().hex[:8]}",
            },
        )
        assert recv.status_code == 201, recv.text
        unit_id = recv.json()["id"]
    else:
        unit_id = units[0]["id"]
    vendors = client.get("/api/v1/logistics/vendors").json()
    cycle = client.post(
        "/api/v1/logistics/rotable-cycles",
        json={"stock_unit_id": unit_id, "cycle_type": "repair", "vendor_id": vendors[0]["id"]},
    )
    assert cycle.status_code == 201, cycle.text
    closed = client.post(
        f"/api/v1/logistics/rotable-cycles/{cycle.json()['id']}/close",
        json={},
    )
    assert closed.status_code == 200, closed.text


def test_warehouse_transfer():
    login_as("operator")
    tree = client.post(
        "/api/v1/logistics/warehouses/tree",
        json={
            "code": f"WH-{uuid.uuid4().hex[:5].upper()}",
            "name": "Secondary",
            "warehouse_type": "physical",
            "building_code": "B2",
            "store_code": "S2",
            "room_code": "R2",
            "zone_types": ["general", "receiving"],
            "bins_per_zone": 1,
        },
    )
    assert tree.status_code == 201, tree.text
    to_wh = tree.json()["warehouse"]["id"]
    to_loc = tree.json()["locations"][0]["id"]
    from_wh = next(w for w in client.get("/api/v1/logistics/warehouses").json() if w["code"] == "WH-MAIN")
    from_loc = next(l for l in client.get("/api/v1/logistics/locations").json() if l["location_type"] == "general" and l["warehouse_id"] == from_wh["id"])
    part = next(p for p in client.get("/api/v1/logistics/parts").json() if p["oem_part_number"] == "MS21042L3")
    client.post(
        "/api/v1/logistics/stock/receive",
        json={"part_master_id": part["id"], "location_id": from_loc["id"], "qty": 3},
    )
    xfer = client.post(
        "/api/v1/logistics/transfers",
        json={
            "from_warehouse_id": from_wh["id"],
            "to_warehouse_id": to_wh,
            "from_location_id": from_loc["id"],
            "to_location_id": to_loc,
            "lines": [{"part_master_id": part["id"], "qty": 1}],
        },
    )
    assert xfer.status_code == 201, xfer.text
    done = client.post(f"/api/v1/logistics/transfers/{xfer.json()['id']}/complete", json={})
    assert done.status_code == 200, done.text


def test_material_planning_reserves_known_part():
    login_as("operator")
    part = next(p for p in client.get("/api/v1/logistics/parts").json() if p["oem_part_number"] == "MS21042L3")
    loc = next(l for l in client.get("/api/v1/logistics/locations").json() if l["location_type"] == "general")
    client.post(
        "/api/v1/logistics/stock/receive",
        json={"part_master_id": part["id"], "location_id": loc["id"], "qty": 10},
    )
    result = client.post(
        "/api/v1/logistics/material-planning/run",
        json={
            "work_package_id": f"wp-{uuid.uuid4().hex[:8]}",
            "auto_purchase_request": True,
            "lines": [{"id": "pline-1", "part_number": "MS21042L3", "qty_required": 2}],
        },
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["reserved_lines"] >= 1
    assert body["lines"][0]["status"] == "ok"


def test_shipment_create():
    login_as("operator")
    ship = client.post(
        "/api/v1/logistics/shipments",
        json={
            "direction": "incoming",
            "courier": "DHL",
            "tracking_number": f"TRK-{uuid.uuid4().hex[:8]}",
            "packing_list": "2 kits sealant",
            "is_import": True,
        },
    )
    assert ship.status_code == 201, ship.text
    listed = client.get("/api/v1/logistics/shipments").json()
    assert any(s["id"] == ship.json()["id"] for s in listed)
