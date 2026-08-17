"""Sprint 7b — personnel, certification, signatures, logbook, alternates, RBAC."""

from __future__ import annotations

import uuid

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()


def _employees_by_number():
    rows = client.get("/api/v1/personnel/employees").json()
    return {e["employee_number"]: e["id"] for e in rows}


def test_personnel_seed_and_rbac():
    login_as("viewer")
    employees = client.get("/api/v1/personnel/employees")
    assert employees.status_code == 200
    numbers = {e["employee_number"] for e in employees.json()}
    assert "E-1001" in numbers
    assert "E-2001" in numbers
    denied = client.post(
        "/api/v1/personnel/employees",
        json={"employee_number": "NOPE", "full_name": "Nope"},
    )
    assert denied.status_code == 403


def test_publication_types_include_fim_and_flight_manuals():
    login_as("operator")
    codes = {t["code"] for t in client.get("/api/v1/publications/types").json()}
    assert "FIM" in codes
    assert "MFIM" in codes
    assert "TSM" in codes
    assert "WDM" in codes
    assert "SDM" in codes
    assert "AFM" in codes
    assert "EO" in codes
    assert "SB" in codes


def test_alternate_parts_and_family_seed():
    login_as("admin")
    families = client.get("/api/v1/fleet/families", params={"manufacturer_id": "mfr-airbus"})
    assert families.status_code == 200
    assert any(f["id"] == "family-a320" or f["code"] == "A320" for f in families.json())

    catalog = client.get("/api/v1/components/catalog", params={"component_type": "engine"}).json()
    assert catalog
    engine_id = catalog[0]["id"]
    suffix = uuid.uuid4().hex[:6].upper()
    alt = client.post(
        "/api/v1/components/catalog",
        json={
            "part_number": f"ALT-ENG-{suffix}",
            "description": "Alternate engine PN",
            "component_type": "engine",
            "ata_chapter_id": "ata-71-00",
        },
    )
    assert alt.status_code == 201, alt.text
    link = client.post(
        "/api/v1/components/catalog/alternates",
        json={
            "catalog_item_id": engine_id,
            "alternate_catalog_item_id": alt.json()["id"],
            "interchangeability": "conditional",
            "conditions": "Same thrust rating",
            "authority_reference": "APT-SEED",
        },
    )
    assert link.status_code == 201, link.text
    listed = client.get(f"/api/v1/components/catalog/{engine_id}/alternates")
    assert listed.status_code == 200
    assert any(a["alternate_catalog_item_id"] == alt.json()["id"] for a in listed.json())


def test_task_engine_types_library_and_audit_trail():
    login_as("operator")
    pub = client.get("/api/v1/publications/pub-amm-a320-71")
    assert pub.status_code == 200
    current_rev = pub.json().get("current_revision_id")
    assert current_rev
    emp = _employees_by_number()

    created = client.post(
        "/api/v1/maintenance/tasks",
        json={
            "task_number": f"MT-SB-{uuid.uuid4().hex[:6].upper()}",
            "task_type": "service_bulletin",
            "aircraft_id": "ac-c-gmea",
            "title": "SB incorporation check",
            "ata_chapter_id": "ata-71-00",
            "priority": "critical",
            "estimated_hours": "3.50",
            "publication_id": "pub-amm-a320-71",
            "required_tools": "Boresscope",
            "required_skills": "Powerplant",
            "required_certification": "AME",
            "requires_inspector": True,
            "independent_inspection_required": False,
            "aca_required": False,
            "assigned_to_employee_id": emp["E-1001"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["task_type"] == "service_bulletin"
    assert body["status"] == "assigned"
    assert body["publication_revision_id"] == current_rev
    assert body["release_status"] == "not_released"
    assert body["version"] == 1

    paused = client.post(
        f"/api/v1/maintenance/tasks/{body['id']}/transition",
        json={"to_status": "started"},
    )
    assert paused.status_code == 200, paused.text
    assert paused.json()["status"] == "started"

    assert (
        client.post(
            f"/api/v1/maintenance/tasks/{body['id']}/certify",
            json={
                "step": "performed",
                "employee_id": emp["E-1001"],
                "method": "password",
                "credential": TEST_AUTH_PASSWORD,
                "actual_hours": "1.25",
            },
        ).status_code
        == 200
    )
    # Segregation of duties: performer cannot also inspect.
    same_person = client.post(
        f"/api/v1/maintenance/tasks/{body['id']}/certify",
        json={
            "step": "inspected",
            "employee_id": emp["E-1001"],
            "method": "pin",
            "credential": "2468",
        },
    )
    assert same_person.status_code == 409

    login_as("reviewer")
    assert (
        client.post(
            f"/api/v1/maintenance/tasks/{body['id']}/certify",
            json={
                "step": "inspected",
                "employee_id": emp["E-2001"],
                "method": "password",
                "credential": TEST_AUTH_PASSWORD,
            },
        ).status_code
        == 200
    )

    login_as("operator")
    # Cannot impersonate another linked employee.
    spoof = client.post(
        f"/api/v1/maintenance/tasks/{body['id']}/certify",
        json={
            "step": "aircraft_released",
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
        },
    )
    assert spoof.status_code == 403

    login_as("reviewer")
    released = client.post(
        f"/api/v1/maintenance/tasks/{body['id']}/certify",
        json={
            "step": "aircraft_released",
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "actual_hours": "2.00",
        },
    )
    assert released.status_code == 200, released.text
    assert released.json()["task"]["release_status"] == "released"
    assert float(released.json()["task"]["actual_hours"]) == 2.0
    assert released.json()["log_entry_id"]

    trail = client.get(f"/api/v1/maintenance/tasks/{body['id']}/audit-trail")
    assert trail.status_code == 200
    assert trail.json()["task"]["task_number"] == body["task_number"]
    assert len(trail.json()["certification_events"]) >= 3
    assert len(trail.json()["signatures"]) >= 3
    assert any(e["task_id"] == body["id"] for e in trail.json()["logbook_entries"])


def test_certification_workflow_and_logbook():
    login_as("operator")
    emp = _employees_by_number()
    policies = client.get("/api/v1/maintenance/critical-policies").json()
    policy_id = next(p["id"] for p in policies if p["domain"] == "landing_gear")

    task = client.post(
        "/api/v1/maintenance/tasks",
        json={
            "task_type": "inspection",
            "aircraft_id": "ac-c-gmea",
            "title": "NLG inspection",
            "ata_chapter_id": "ata-32-00",
            "critical_policy_id": policy_id,
            "publication_id": "pub-amm-a320-71",
        },
    )
    assert task.status_code == 201, task.text
    task_body = task.json()
    assert task_body["task_number"]
    assert task_body["publication_revision_id"]
    task_id = task_body["id"]

    performed = client.post(
        f"/api/v1/maintenance/tasks/{task_id}/certify",
        json={
            "step": "performed",
            "employee_id": emp["E-1001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "notes": "Work performed",
        },
    )
    assert performed.status_code == 200, performed.text

    login_as("reviewer")
    inspected = client.post(
        f"/api/v1/maintenance/tasks/{task_id}/certify",
        json={
            "step": "inspected",
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
        },
    )
    assert inspected.status_code == 200, inspected.text

    aca = client.post(
        f"/api/v1/maintenance/tasks/{task_id}/certify",
        json={
            "step": "aca_certified",
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
        },
    )
    assert aca.status_code == 200, aca.text

    login_as("operator")
    release_denied = client.post(
        f"/api/v1/maintenance/tasks/{task_id}/certify",
        json={
            "step": "aircraft_released",
            "employee_id": emp["E-1001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
        },
    )
    assert release_denied.status_code == 403

    login_as("reviewer")
    released = client.post(
        f"/api/v1/maintenance/tasks/{task_id}/certify",
        json={
            "step": "aircraft_released",
            "employee_id": emp["E-2001"],
            "method": "password",
            "credential": TEST_AUTH_PASSWORD,
            "notes": "Released to service",
        },
    )
    assert released.status_code == 200, released.text
    assert released.json()["task"]["status"] == "released"
    assert released.json()["log_entry_id"]

    logbook = client.get("/api/v1/maintenance/logbook", params={"aircraft_id": "ac-c-gmea"})
    assert logbook.status_code == 200
    entry = next(e for e in logbook.json() if e["task_id"] == task_id)
    assert entry["mechanic_employee_id"] == emp["E-1001"]
    assert entry["inspector_employee_id"] == emp["E-2001"]
    assert entry["aca_employee_id"] == emp["E-2001"]
    assert "aircraft_history=true" in entry["details"]
    assert "signature_chain=" in entry["details"]
    assert "revision_number=" in entry["details"]
    assert "required_certification=" in entry["details"]

    login_as("operator")
    amended = client.post(
        f"/api/v1/maintenance/logbook/{entry['id']}/amend",
        json={"reason": "Corrected ATA reference note", "summary": "Amendment"},
    )
    assert amended.status_code == 201, amended.text
    assert f"amendment_of={entry['id']}" in amended.json()["details"]
    # Original remains unchanged (immutable).
    original = next(e for e in client.get("/api/v1/maintenance/logbook", params={"aircraft_id": "ac-c-gmea"}).json() if e["id"] == entry["id"])
    assert "amendment_of=" not in original["details"]

    login_as("admin")
    events = client.get("/admin/audit", params={"action": "maintenance.certify", "limit": 50})
    assert events.status_code == 200


def test_tenant_isolation_maintenance_and_publications():
    login_as("operator")
    assert client.get("/api/v1/maintenance/tasks", params={"organization_id": "org-aviation-west"}).status_code == 403
    assert client.get("/api/v1/publications", params={"organization_id": "org-aviation-west"}).status_code == 403


def test_ai_stubs_no_compute():
    login_as("operator")
    created = client.post(
        "/api/v1/maintenance/ai/index-stubs",
        json={
            "source_type": "publication",
            "source_id": "pub-amm-a320-71",
            "title": "AMM index stub",
            "ata_chapter_id": "ata-71-00",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] in {"pending_index", "pending"}
    listed = client.get("/api/v1/maintenance/ai/index-stubs")
    assert listed.status_code == 200
    assert any(i["source_id"] == "pub-amm-a320-71" for i in listed.json())
