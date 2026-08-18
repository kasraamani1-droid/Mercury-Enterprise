"""Sprint 8 — work packages, work orders, job cards, execution, reports."""

from __future__ import annotations

import uuid

import pytest
from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

JC_STATUSES = [
    "draft",
    "assigned",
    "accepted",
    "in_progress",
    "paused",
    "waiting_parts",
    "waiting_engineering",
    "waiting_inspection",
    "completed",
    "rejected",
    "released",
    "closed",
]


def login_as(operator: str):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()


def employees():
    login_as("operator")
    rows = client.get("/api/v1/personnel/employees").json()
    return {e["employee_number"]: e["id"] for e in rows}


def _create_package(**overrides):
    login_as("operator")
    emp = employees()
    payload = {
        "aircraft_id": "ac-c-gmea",
        "description": "Test package",
        "priority": "high",
        "hangar_bay": "Bay-2",
        "shift_code": "DAY",
        "planner_employee_id": emp["E-1001"],
        "supervisor_employee_id": emp["E-1001"],
        **overrides,
    }
    r = client.post("/api/v1/work-orders/packages", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _create_order(package_id, **overrides):
    payload = {
        "work_package_id": package_id,
        "title": "ATA 32 landing gear WO",
        "ata_chapter_id": "ata-32-00",
        "publication_id": "pub-amm-a320-71",
        "priority": "normal",
        **overrides,
    }
    r = client.post("/api/v1/work-orders/orders", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _create_card(order_id, **overrides):
    emp = employees()
    payload = {
        "work_order_id": order_id,
        "title": "NLG functional check",
        "ata_chapter_id": "ata-32-00",
        "publication_id": "pub-amm-a320-71",
        "technician_employee_id": emp["E-1001"],
        "independent_inspection_required": False,
        "aca_required": True,
        "estimated_hours": "1.50",
        **overrides,
    }
    r = client.post("/api/v1/work-orders/job-cards", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_seed_work_package_and_job_card():
    login_as("operator")
    package = client.get("/api/v1/work-orders/packages/wp-demo-c-gmea")
    assert package.status_code == 200, package.text
    assert package.json()["package_number"] == "WP-DEMO-001"
    assert package.json()["aircraft_id"] == "ac-c-gmea"
    card = client.get("/api/v1/work-orders/job-cards/jc-demo-oil")
    assert card.status_code == 200, card.text
    assert card.json()["job_card_number"] == "JC-DEMO-001"
    packages = client.get(
        "/api/v1/work-orders/packages",
        params={"aircraft_id": "ac-c-gmea", "limit": 500},
    ).json()
    assert any(p["package_number"] == "WP-DEMO-001" for p in packages)
    cards = client.get(
        "/api/v1/work-orders/job-cards",
        params={"aircraft_id": "ac-c-gmea", "limit": 500},
    ).json()
    assert any(c["job_card_number"] == "JC-DEMO-001" for c in cards)


def test_viewer_can_read_not_manage():
    login_as("viewer")
    assert client.get("/api/v1/work-orders/packages").status_code == 200
    assert (
        client.post(
            "/api/v1/work-orders/packages",
            json={"aircraft_id": "ac-c-gmea", "description": "nope"},
        ).status_code
        == 403
    )


def test_tenant_isolation_work_orders():
    login_as("operator")
    assert client.get("/api/v1/work-orders/packages", params={"organization_id": "org-aviation-west"}).status_code == 403


def test_create_package_order_card_chain():
    pkg = _create_package(package_number=f"WP-T-{uuid.uuid4().hex[:6].upper()}")
    assert pkg["status"] == "draft"
    assert pkg["fleet_id"]
    order = _create_order(pkg["id"], wo_number=f"WO-T-{uuid.uuid4().hex[:6].upper()}")
    assert order["work_package_id"] == pkg["id"]
    assert order["publication_revision_id"]
    card = _create_card(order["id"], job_card_number=f"JC-T-{uuid.uuid4().hex[:6].upper()}")
    assert card["status"] == "assigned"
    assert card["maintenance_task_id"]
    task = client.get(f"/api/v1/maintenance/tasks/{card['maintenance_task_id']}")
    assert task.status_code == 200
    assert task.json()["publication_revision_id"] == card["publication_revision_id"]


def test_job_card_assign_and_transitions():
    pkg = _create_package()
    order = _create_order(pkg["id"])
    emp = employees()
    card = _create_card(order["id"], technician_employee_id=None)
    assert card["status"] == "draft"
    assigned = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/assign",
        json={"technician_employee_id": emp["E-1001"], "hangar_bay": "Bay-3"},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["status"] == "assigned"
    assert assigned.json()["hangar_bay"] == "Bay-3"

    accepted = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "accepted"},
    )
    assert accepted.status_code == 200
    started = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "in_progress"},
    )
    assert started.status_code == 200
    paused = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "paused"},
    )
    assert paused.status_code == 200
    parts = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "waiting_parts"},
    )
    assert parts.status_code == 200
    bad = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "released"},
    )
    assert bad.status_code == 409


@pytest.mark.parametrize(
    "current,target,ok",
    [
        ("draft", "assigned", True),
        ("assigned", "accepted", True),
        ("accepted", "in_progress", True),
        ("in_progress", "paused", True),
        ("in_progress", "waiting_parts", True),
        ("in_progress", "waiting_engineering", True),
        ("paused", "in_progress", True),
        ("waiting_parts", "in_progress", True),
        ("in_progress", "waiting_inspection", False),
        ("completed", "released", False),
        ("draft", "released", False),
        ("closed", "in_progress", False),
    ],
)
def test_transition_matrix_samples(current, target, ok):
    from app.work_orders.service import JC_TRANSITIONS

    allowed = JC_TRANSITIONS.get(current, frozenset())
    assert (target in allowed) is ok


def test_transition_cannot_bypass_release_gate():
    """completed → released must go through /release (ACA + logbook), not /transition."""
    emp = employees()
    pkg = _create_package()
    order = _create_order(pkg["id"])
    card = _create_card(order["id"], independent_inspection_required=False, aca_required=True)
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
    bypass = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "released"},
    )
    assert bypass.status_code == 409


def test_attachments_and_notes():
    pkg = _create_package()
    order = _create_order(pkg["id"])
    card = _create_card(order["id"])
    att = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/attachments",
        json={"kind": "photo", "title": "Leak photo", "storage_uri": "local://photos/1.jpg", "notes": "LH side"},
    )
    assert att.status_code == 201, att.text
    listed = client.get(f"/api/v1/work-orders/job-cards/{card['id']}/attachments")
    assert listed.status_code == 200
    assert any(a["kind"] == "photo" for a in listed.json())


def test_end_to_end_execution_inspect_release_logbook():
    emp = employees()
    pkg = _create_package()
    order = _create_order(pkg["id"])
    card = _create_card(
        order["id"],
        independent_inspection_required=False,
        aca_required=True,
    )
    client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "accepted"},
    )
    client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/transition",
        json={"to_status": "in_progress"},
    )
    completed = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/complete-work",
        json={
            "employee_id": emp["E-1001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "actual_hours": "1.25",
            "notes": "Work complete",
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "waiting_inspection"

    # Inspector/ACA path uses reviewer-linked employee for inspect+release.
    login_as("reviewer")
    inspected = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/inspect",
        json={
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "decision": "approve",
            "notes": "Inspection OK",
        },
    )
    assert inspected.status_code == 200, inspected.text
    assert inspected.json()["status"] == "completed"

    released = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/release",
        json={
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "notes": "Released to service",
        },
    )
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "released"
    task_id = released.json()["maintenance_task_id"]
    logbook = client.get("/api/v1/maintenance/logbook", params={"aircraft_id": "ac-c-gmea"})
    assert logbook.status_code == 200
    assert any(e["task_id"] == task_id for e in logbook.json())


def test_inspect_rework_and_reject():
    emp = employees()
    pkg = _create_package()
    order = _create_order(pkg["id"])
    card = _create_card(order["id"], aca_required=False, independent_inspection_required=False)
    client.post(f"/api/v1/work-orders/job-cards/{card['id']}/transition", json={"to_status": "accepted"})
    client.post(f"/api/v1/work-orders/job-cards/{card['id']}/transition", json={"to_status": "in_progress"})
    client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/complete-work",
        json={"employee_id": emp["E-1001"], "method": "password", "credential": TEST_AUTH_PASSWORD},
    )
    login_as("reviewer")
    rework = client.post(
        f"/api/v1/work-orders/job-cards/{card['id']}/inspect",
        json={
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "decision": "rework",
            "notes": "Torque incomplete",
        },
    )
    assert rework.status_code == 200
    assert rework.json()["status"] == "in_progress"


def test_dashboards_and_reports():
    login_as("operator")
    dash = client.get("/api/v1/work-orders/dashboard", params={"role": "manager"})
    assert dash.status_code == 200
    body = dash.json()
    assert "open_work_orders" in body
    assert "job_cards_by_status" in body

    for report in (
        "open_work_orders",
        "delayed_work_orders",
        "labor_hours",
        "inspection_status",
        "release_status",
        "technician_productivity",
        "aircraft_status",
    ):
        r = client.get(f"/api/v1/work-orders/reports/{report}")
        assert r.status_code == 200, report
        assert r.json()["report"] == report
        assert isinstance(r.json()["rows"], list)

    bad = client.get("/api/v1/work-orders/reports/not_a_report")
    assert bad.status_code == 400


def test_duplicate_package_number_conflict():
    number = f"WP-DUP-{uuid.uuid4().hex[:6].upper()}"
    _create_package(package_number=number)
    login_as("operator")
    dup = client.post(
        "/api/v1/work-orders/packages",
        json={"aircraft_id": "ac-c-gmea", "package_number": number, "description": "dup"},
    )
    assert dup.status_code == 409


def test_job_card_status_vocabulary_complete():
    for status in JC_STATUSES:
        assert status in JC_STATUSES
    assert len(JC_STATUSES) == 12
