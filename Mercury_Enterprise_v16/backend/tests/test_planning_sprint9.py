"""Sprint 9 — maintenance planning, MPD, forecast, AD/SB/EO, MEL, defects."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

HORIZONS = [30, 90, 180, 365]
CHECK_TYPES = [
    "preflight",
    "transit",
    "daily",
    "weekly",
    "service",
    "a",
    "b",
    "c",
    "d",
    "structural",
    "engine",
    "landing_gear",
    "special",
    "custom",
]


def login_as(operator: str):
    r = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert r.status_code == 200
    return r.json()


def test_seed_program_and_mpd():
    login_as("operator")
    programs = client.get("/api/v1/planning/programs").json()
    assert any(p["program_code"] == "MP-A320-LINE" for p in programs)
    mpd = client.get("/api/v1/planning/mpd-tasks").json()
    assert any(t["task_number"] == "MPD-05-00-00-A" for t in mpd)


def test_viewer_can_read_not_manage():
    login_as("viewer")
    assert client.get("/api/v1/planning/programs").status_code == 200
    assert (
        client.post(
            "/api/v1/planning/programs",
            json={"program_code": "X", "title": "Nope"},
        ).status_code
        == 403
    )


def test_tenant_isolation_planning():
    login_as("operator")
    assert client.get("/api/v1/planning/programs", params={"organization_id": "org-aviation-west"}).status_code == 403


def test_create_program_revision_immutable():
    login_as("operator")
    code = f"MP-T-{uuid.uuid4().hex[:6].upper()}"
    created = client.post(
        "/api/v1/planning/programs",
        json={
            "program_code": code,
            "title": "Test Program",
            "manufacturer": "Airbus",
            "aircraft_family": "A320",
            "revision_number": "1",
        },
    )
    assert created.status_code == 201, created.text
    pid = created.json()["id"]
    rev1 = created.json()["current_revision_id"]
    rev2 = client.post(
        f"/api/v1/planning/programs/{pid}/revisions",
        json={"revision_number": "2", "activate": True, "notes": "New rev"},
    )
    assert rev2.status_code == 201, rev2.text
    assert rev2.json()["id"] != rev1
    listed = client.get(f"/api/v1/planning/programs/{pid}/revisions").json()
    assert len(listed) >= 2
    assert any(r["status"] == "superseded" for r in listed)


def test_create_mpd_task():
    login_as("operator")
    programs = client.get("/api/v1/planning/programs").json()
    rev = programs[0]["current_revision_id"]
    r = client.post(
        "/api/v1/planning/mpd-tasks",
        json={
            "program_revision_id": rev,
            "task_number": f"MPD-T-{uuid.uuid4().hex[:5].upper()}",
            "title": "Zone inspection",
            "ata_chapter_id": "ata-53-00",
            "interval_calendar_days": 30,
            "interval_flight_hours": "100.00",
            "required_ii": True,
            "required_aca": True,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["required_ii"] is True


@pytest.mark.parametrize("check_type", CHECK_TYPES)
def test_check_types_accepted(check_type):
    login_as("operator")
    r = client.post(
        "/api/v1/planning/checks",
        json={
            "aircraft_id": "ac-c-gmea",
            "check_code": f"CHK-{check_type[:3].upper()}-{uuid.uuid4().hex[:4].upper()}",
            "check_type": check_type,
            "title": f"{check_type} check",
            "interval_calendar_days": 7,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["check_type"] == check_type


@pytest.mark.parametrize("horizon", HORIZONS)
def test_forecast_horizons(horizon):
    login_as("operator")
    r = client.get("/api/v1/planning/forecast", params={"horizon_days": horizon})
    assert r.status_code == 200
    body = r.json()
    assert body["horizon_days"] == horizon
    assert "overdue" in body and "due_soon" in body and "future" in body


def test_due_list_sorted_by_urgency():
    login_as("operator")
    r = client.get("/api/v1/planning/due-list")
    assert r.status_code == 200
    items = r.json()["items"]
    rank = {"overdue": 0, "due_soon": 1, "future": 2}
    ranks = [rank.get(i["urgency"], 9) for i in items]
    assert ranks == sorted(ranks)


def test_ad_sb_eo_create_and_approve():
    login_as("operator")
    ad = client.post(
        "/api/v1/planning/ads",
        json={
            "ad_number": f"AD-T-{uuid.uuid4().hex[:6].upper()}",
            "authority": "easa",
            "title": "EASA demo AD",
            "mandatory": True,
            "due_date": (datetime.utcnow() + timedelta(days=40)).isoformat(),
        },
    )
    assert ad.status_code == 201, ad.text
    sb = client.post(
        "/api/v1/planning/service-bulletins",
        json={
            "sb_number": f"SB-T-{uuid.uuid4().hex[:6].upper()}",
            "sb_type": "asb",
            "title": "Alert SB",
            "priority": "mandatory",
        },
    )
    assert sb.status_code == 201, sb.text
    eo = client.post(
        "/api/v1/planning/engineering-orders",
        json={"eo_number": f"EO-T-{uuid.uuid4().hex[:6].upper()}", "title": "Bonding EO"},
    )
    assert eo.status_code == 201
    approved = client.post(f"/api/v1/planning/engineering-orders/{eo.json()['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_mel_and_deferred_defect():
    login_as("operator")
    mel = client.post(
        "/api/v1/planning/mel-items",
        json={
            "list_type": "mel",
            "item_number": f"33-{uuid.uuid4().hex[:3]}",
            "title": "Nav light",
            "dispatch_category": "B",
            "repair_interval_days": 3,
        },
    )
    assert mel.status_code == 201, mel.text
    defect = client.post(
        "/api/v1/planning/deferred-defects",
        json={
            "aircraft_id": "ac-c-gmea",
            "title": "Nav light inop",
            "deferral_type": "mel",
            "mel_item_id": mel.json()["id"],
            "dispatch_category": "B",
            "repair_interval_days": 3,
        },
    )
    assert defect.status_code == 201, defect.text
    assert defect.json()["status"] == "deferred"
    assert defect.json()["expires_at"]


def test_cdl_item():
    login_as("operator")
    r = client.post(
        "/api/v1/planning/mel-items",
        json={
            "list_type": "cdl",
            "item_number": f"CDL-{uuid.uuid4().hex[:4].upper()}",
            "title": "Fairing missing",
            "dispatch_category": "D",
        },
    )
    assert r.status_code == 201
    assert r.json()["list_type"] == "cdl"


def test_planner_dashboard_and_aircraft_status():
    login_as("operator")
    dash = client.get("/api/v1/planning/dashboard")
    assert dash.status_code == 200
    body = dash.json()
    assert "checks_due" in body
    assert "deferred_defects" in body
    assert "traffic_lights" in body
    status = client.get("/api/v1/planning/aircraft-status")
    assert status.status_code == 200
    assert any(a["aircraft_id"] == "ac-c-gmea" for a in status.json())


def test_hangar_plan_and_utilization():
    login_as("operator")
    util = client.put(
        "/api/v1/planning/utilization",
        json={
            "aircraft_id": "ac-c-gmea",
            "location": "YUL Bay-3",
            "ops_status": "maintenance",
            "flight_hours": "12600.00",
            "flight_cycles": 8300,
            "engine_hours": "11900.00",
            "apu_hours": "2150.00",
        },
    )
    assert util.status_code == 200, util.text
    plan = client.post(
        "/api/v1/planning/hangar-plans",
        json={
            "aircraft_id": "ac-c-gmea",
            "hangar": "Hangar-1",
            "bay": "Bay-3",
            "team_name": "Heavy Team",
            "shift_code": "NIGHT",
            "critical_path": True,
            "estimated_duration_hours": "48.00",
        },
    )
    assert plan.status_code == 201, plan.text
    assert plan.json()["critical_path"] is True


def test_generate_work_package_from_check():
    login_as("operator")
    # Fresh check without generated package
    chk = client.post(
        "/api/v1/planning/checks",
        json={
            "aircraft_id": "ac-c-gmea",
            "program_revision_id": "mpr-a320-line-1",
            "check_code": f"A-GEN-{uuid.uuid4().hex[:5].upper()}",
            "check_type": "a",
            "title": "Generate package check",
            "interval_calendar_days": 60,
            "bay": "Bay-1",
            "hangar": "Hangar-1",
        },
    )
    assert chk.status_code == 201, chk.text
    gen = client.post(
        "/api/v1/planning/checks/generate-package",
        json={"check_id": chk.json()["id"], "include_mpd_tasks": True, "max_job_cards": 5},
    )
    assert gen.status_code == 201, gen.text
    body = gen.json()
    assert body["work_package_id"]
    assert body["job_card_ids"]
    # Duplicate blocked
    again = client.post(
        "/api/v1/planning/checks/generate-package",
        json={"check_id": chk.json()["id"]},
    )
    assert again.status_code == 409
    # Sprint 8 package exists
    pkg = client.get(f"/api/v1/work-orders/packages/{body['work_package_id']}")
    assert pkg.status_code == 200


def test_forecast_includes_seed_check_and_ad():
    login_as("operator")
    fc = client.get("/api/v1/planning/forecast", params={"horizon_days": 90}).json()
    sources = {i["source_type"] for i in fc["overdue"] + fc["due_soon"] + fc["future"]}
    assert "check" in sources or "ad" in sources


def test_audit_program_create():
    login_as("operator")
    code = f"MP-AUD-{uuid.uuid4().hex[:5].upper()}"
    created = client.post(
        "/api/v1/planning/programs",
        json={"program_code": code, "title": "Audit program"},
    )
    assert created.status_code == 201
    login_as("admin")
    events = client.get("/admin/audit", params={"action": "planning.program.create", "limit": 50})
    assert events.status_code == 200
    assert any(e.get("target_id") == created.json()["id"] for e in events.json())
