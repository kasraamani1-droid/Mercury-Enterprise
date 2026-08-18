"""Sprint 8 — full job-card transition matrix, RBAC, and execution edge cases."""

from __future__ import annotations

import uuid

import pytest
from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app
from app.work_orders.service import JC_STATUSES, JC_TRANSITIONS

client = TestClient(app)

# Frozen contract — must stay in sync with WorkOrderService.JC_TRANSITIONS.
# Certification gates are intentionally unreachable via /transition.
EXPECTED_JC_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"assigned", "closed"}),
    "assigned": frozenset({"accepted", "draft", "closed"}),
    "accepted": frozenset({"in_progress", "waiting_parts", "waiting_engineering", "closed"}),
    "in_progress": frozenset({"paused", "waiting_parts", "waiting_engineering", "closed"}),
    "paused": frozenset({"in_progress", "waiting_parts", "waiting_engineering", "closed"}),
    "waiting_parts": frozenset({"in_progress", "accepted", "closed"}),
    "waiting_engineering": frozenset({"in_progress", "accepted", "closed"}),
    "waiting_inspection": frozenset(),
    "completed": frozenset(),
    "rejected": frozenset({"in_progress", "assigned", "closed"}),
    "released": frozenset({"closed"}),
    "closed": frozenset(),
}

DASHBOARD_ROLES = ["manager", "planner", "supervisor", "technician", "qa", "aca"]
REPORTS = [
    "open_work_orders",
    "delayed_work_orders",
    "labor_hours",
    "aircraft_status",
    "technician_productivity",
    "inspection_status",
    "release_status",
]


def login_as(operator: str):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()


def employees():
    login_as("operator")
    rows = client.get("/api/v1/personnel/employees").json()
    return {e["employee_number"]: e["id"] for e in rows}


def _pkg_order_card(*, independent: bool = False, aca: bool = True, tech: bool = True):
    emp = employees()
    pkg = client.post(
        "/api/v1/work-orders/packages",
        json={
            "aircraft_id": "ac-c-gmea",
            "description": "Matrix package",
            "priority": "normal",
            "hangar_bay": "Bay-A",
            "shift_code": "NIGHT",
            "package_number": f"WP-M-{uuid.uuid4().hex[:6].upper()}",
        },
    ).json()
    order = client.post(
        "/api/v1/work-orders/orders",
        json={
            "work_package_id": pkg["id"],
            "title": "Matrix WO",
            "ata_chapter_id": "ata-32-00",
            "publication_id": "pub-amm-a320-71",
            "wo_number": f"WO-M-{uuid.uuid4().hex[:6].upper()}",
        },
    ).json()
    card = client.post(
        "/api/v1/work-orders/job-cards",
        json={
            "work_order_id": order["id"],
            "title": "Matrix JC",
            "ata_chapter_id": "ata-32-00",
            "publication_id": "pub-amm-a320-71",
            "technician_employee_id": emp["E-1001"] if tech else None,
            "independent_inspection_required": independent,
            "aca_required": aca,
            "estimated_hours": "2.00",
            "job_card_number": f"JC-M-{uuid.uuid4().hex[:6].upper()}",
        },
    ).json()
    return pkg, order, card, emp


def test_jc_transition_matrix_matches_contract():
    assert set(JC_STATUSES) == set(EXPECTED_JC_TRANSITIONS)
    assert set(JC_TRANSITIONS) == set(EXPECTED_JC_TRANSITIONS)
    for status, edges in EXPECTED_JC_TRANSITIONS.items():
        assert JC_TRANSITIONS[status] == edges


@pytest.mark.parametrize(
    "current,target",
    [(src, tgt) for src in sorted(EXPECTED_JC_TRANSITIONS) for tgt in sorted(JC_STATUSES)],
)
def test_jc_transition_matrix_complete(current, target):
    """Every status pair is either an allowed edge or explicitly forbidden."""
    allowed = target in EXPECTED_JC_TRANSITIONS[current]
    assert (target in JC_TRANSITIONS[current]) is allowed
    if current == target:
        assert not allowed


@pytest.mark.parametrize(
    "current,target",
    [(src, tgt) for src, allowed in EXPECTED_JC_TRANSITIONS.items() for tgt in sorted(allowed)],
)
def test_jc_allowed_transitions_enumerated(current, target):
    assert target in JC_TRANSITIONS[current]
    assert current in JC_STATUSES
    assert target in JC_STATUSES


@pytest.mark.parametrize("role", DASHBOARD_ROLES)
def test_dashboard_roles(role):
    login_as("operator")
    r = client.get("/api/v1/work-orders/dashboard", params={"role": role})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == role
    assert "job_cards_by_status" in body
    assert isinstance(body["open_work_orders"], int)


@pytest.mark.parametrize("report", REPORTS)
def test_each_report_type(report):
    login_as("operator")
    r = client.get(f"/api/v1/work-orders/reports/{report}")
    assert r.status_code == 200
    body = r.json()
    assert body["report"] == report
    assert isinstance(body["rows"], list)


def test_get_package_order_card_by_id():
    pkg, order, card, _ = _pkg_order_card()
    assert client.get(f"/api/v1/work-orders/packages/{pkg['id']}").status_code == 200
    assert client.get(f"/api/v1/work-orders/orders/{order['id']}").status_code == 200
    assert client.get(f"/api/v1/work-orders/job-cards/{card['id']}").status_code == 200
    assert client.get("/api/v1/work-orders/packages/missing-id").status_code == 404


def test_operator_cannot_release_without_permission():
    _, _, card, emp = _pkg_order_card(independent=False)
    client.post(f"/api/v1/work-orders/job-cards/{card['id']}/transition", json={"to_status": "accepted"})
    client.post(f"/api/v1/work-orders/job-cards/{card['id']}/transition", json={"to_status": "in_progress"})
    client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/complete-work",
        json={"employee_id": emp["E-1001"], "method": "password", "credential": TEST_AUTH_PASSWORD},
    )
    login_as("reviewer")
    client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/inspect",
        json={
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "decision": "approve",
        },
    )
    login_as("operator")
    denied = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/release",
        json={
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
        },
    )
    assert denied.status_code == 403


def test_viewer_cannot_execute_transitions():
    _, _, card, _ = _pkg_order_card()
    login_as("viewer")
    r = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "accepted"},
    )
    assert r.status_code == 403


def test_invalid_priority_rejected():
    login_as("operator")
    r = client.post(
        "/api/v1/work-orders/packages",
        json={"aircraft_id": "ac-c-gmea", "description": "bad", "priority": "urgent"},
    )
    assert r.status_code in {400, 422}


def test_duplicate_wo_and_jc_numbers():
    pkg, order, card, emp = _pkg_order_card()
    login_as("operator")
    dup_wo = client.post(
        "/api/v1/work-orders/orders",
        json={
            "work_package_id": pkg["id"],
            "title": "dup",
            "wo_number": order["wo_number"],
        },
    )
    assert dup_wo.status_code == 409
    dup_jc = client.post(
        "/api/v1/work-orders/job-cards",
        json={
            "work_order_id": order["id"],
            "title": "dup card",
            "job_card_number": card["job_card_number"],
            "technician_employee_id": emp["E-1001"],
        },
    )
    assert dup_jc.status_code == 409


def test_hour_rollup_on_complete():
    _, order, card, emp = _pkg_order_card()
    client.post(f"/api/v1/work-orders/job-cards/{card['id']}/transition", json={"to_status": "accepted"})
    client.post(f"/api/v1/work-orders/job-cards/{card['id']}/transition", json={"to_status": "in_progress"})
    done = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/complete-work",
        json={
            "employee_id": emp["E-1001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "actual_hours": "3.50",
        },
    )
    assert done.status_code == 200
    assert done.json()["actual_hours"] in ("3.50", "3.5", 3.5)
    refreshed = client.get(f"/api/v1/work-orders/orders/{order['id']}").json()
    assert float(refreshed["actual_hours"]) >= 3.5


def test_waiting_engineering_and_parts_path():
    _, _, card, _ = _pkg_order_card()
    for step in ("accepted", "in_progress", "waiting_engineering"):
        r = client.post(
            f"/api/v1/work-orders/job-cards/{card['id']}/transition",
            json={"to_status": step},
        )
        assert r.status_code == 200, step
    r = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "in_progress"},
    )
    assert r.status_code == 200
    r = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "waiting_parts"},
    )
    assert r.status_code == 200


def test_reject_inspection_path():
    _, _, card, emp = _pkg_order_card()
    client.post(f"/api/v1/work-orders/job-cards/{card['id']}/transition", json={"to_status": "accepted"})
    client.post(f"/api/v1/work-orders/job-cards/{card['id']}/transition", json={"to_status": "in_progress"})
    client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/complete-work",
        json={"employee_id": emp["E-1001"], "method": "password", "credential": TEST_AUTH_PASSWORD},
    )
    login_as("reviewer")
    rejected = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/inspect",
        json={
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "decision": "reject",
            "notes": "NCR raised",
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_independent_inspection_required_blocks_release_until_done():
    _, _, card, emp = _pkg_order_card(independent=True, aca=True)
    assert "E-3001" in emp
    client.post(f"/api/v1/work-orders/job-cards/{card['id']}/transition", json={"to_status": "accepted"})
    client.post(f"/api/v1/work-orders/job-cards/{card['id']}/transition", json={"to_status": "in_progress"})
    client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/complete-work",
        json={"employee_id": emp["E-1001"], "method": "password", "credential": TEST_AUTH_PASSWORD},
    )
    login_as("reviewer")
    approved = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/inspect",
        json={
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "decision": "approve",
        },
    )
    assert approved.status_code == 200, approved.text
    blocked = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/release",
        json={
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
        },
    )
    assert blocked.status_code == 409

    login_as("admin")
    ii = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/inspect",
        json={
            "employee_id": emp["E-3001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "decision": "independent_inspection",
            "notes": "II complete",
        },
    )
    assert ii.status_code == 200, ii.text

    login_as("reviewer")
    released = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/release",
        json={
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "notes": "Released after II",
        },
    )
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "released"


def test_close_from_draft():
    _, _, card, _ = _pkg_order_card(tech=False)
    assert card["status"] == "draft"
    closed = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "closed"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"


def test_photo_attachment_kind():
    _, _, card, _ = _pkg_order_card()
    r = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/attachments",
        json={
            "kind": "photo",
            "title": "Bay photo",
            "storage_uri": "local://hangar/bay-a.jpg",
            "content_type": "image/jpeg",
        },
    )
    assert r.status_code == 201
    assert r.json()["kind"] == "photo"


def test_list_filters_by_status_and_aircraft():
    login_as("operator")
    cards = client.get(
        "/api/v1/work-orders/job-cards",
        params={"aircraft_id": "ac-c-gmea", "status": "assigned", "limit": 50},
    )
    assert cards.status_code == 200
    assert all(c["aircraft_id"] == "ac-c-gmea" for c in cards.json())
    pkgs = client.get("/api/v1/work-orders/packages", params={"aircraft_id": "ac-c-gmea"})
    assert pkgs.status_code == 200


def test_audit_events_for_job_card_create():
    _, _, card, _ = _pkg_order_card()
    login_as("admin")
    audit = client.get("/admin/audit", params={"action": "job_card.create", "limit": 50})
    assert audit.status_code == 200
    rows = audit.json()
    assert any(row.get("target_id") == card["id"] or "job_card" in str(row.get("action", "")) for row in rows)


@pytest.mark.parametrize("priority", ["low", "normal", "high", "critical"])
def test_package_priorities(priority):
    login_as("operator")
    r = client.post(
        "/api/v1/work-orders/packages",
        json={
            "aircraft_id": "ac-c-gmea",
            "description": f"prio {priority}",
            "priority": priority,
            "package_number": f"WP-P-{priority[:3].upper()}-{uuid.uuid4().hex[:4].upper()}",
        },
    )
    assert r.status_code == 201
    assert r.json()["priority"] == priority
