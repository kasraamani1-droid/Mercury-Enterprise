"""Program A — Enterprise Platform Foundation API tests."""

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


def test_platform_seed_overview_and_templates():
    login_as("operator")
    overview = client.get("/api/v1/platform/overview")
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["organization_id"] == "org-aviation-east"
    assert body["facilities"] >= 1
    assert body["workflow_definitions"] >= 1
    templates = client.get("/api/v1/platform/rbac/templates")
    assert templates.status_code == 200
    codes = {t["code"] for t in templates.json()}
    assert "aviation.technician" in codes
    assert "platform.admin" in codes
    flags = client.get("/api/v1/platform/feature-flags")
    assert flags.status_code == 200
    assert any(f["code"] == "platform.workflow_engine" for f in flags.json())


def test_viewer_can_read_not_manage():
    login_as("viewer")
    assert client.get("/api/v1/platform/overview").status_code == 200
    assert (
        client.post(
            "/api/v1/platform/org/facilities",
            json={"code": "X", "name": "Nope", "facility_type": "hangar"},
        ).status_code
        == 403
    )


def test_tenant_isolation_platform():
    login_as("operator")
    assert (
        client.get("/api/v1/platform/org/facilities", params={"organization_id": "org-aviation-west"}).status_code
        == 403
    )


def test_business_unit_cost_center_facility():
    login_as("operator")
    suffix = uuid.uuid4().hex[:6].upper()
    bu = client.post(
        "/api/v1/platform/org/business-units",
        json={"code": f"BU-{suffix}", "name": "East Ops", "country_code": "US"},
    )
    assert bu.status_code == 201, bu.text
    cc = client.post(
        "/api/v1/platform/org/cost-centers",
        json={
            "code": f"CC-{suffix}",
            "name": "Hangar Cost",
            "business_unit_id": bu.json()["id"],
        },
    )
    assert cc.status_code == 201, cc.text
    fac = client.post(
        "/api/v1/platform/org/facilities",
        json={"code": f"HGR-{suffix}", "name": "Hangar Test", "facility_type": "hangar"},
    )
    assert fac.status_code == 201, fac.text
    listed = client.get("/api/v1/platform/org/facilities", params={"facility_type": "hangar"})
    assert listed.status_code == 200
    assert any(f["code"] == f"HGR-{suffix}" for f in listed.json())


def test_api_key_pat_mfa():
    login_as("operator")
    key = client.post(
        "/api/v1/platform/identity/api-keys",
        json={"name": "CI Integration", "scopes": "platform.read"},
    )
    assert key.status_code == 201, key.text
    body = key.json()
    assert body["secret"]
    assert body["key_prefix"]
    assert body["status"] == "active"
    revoked = client.post(f"/api/v1/platform/identity/api-keys/{body['id']}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    pat = client.post(
        "/api/v1/platform/identity/pats",
        json={"name": "Dev PAT", "scopes": "platform.read"},
    )
    assert pat.status_code == 201, pat.text
    assert pat.json()["secret"]
    pat_id = pat.json()["id"]
    assert client.post(f"/api/v1/platform/identity/pats/{pat_id}/revoke").status_code == 200

    mfa = client.post("/api/v1/platform/identity/mfa/enroll", json={"method": "totp"})
    assert mfa.status_code == 201, mfa.text
    assert mfa.json()["setup_ref"].startswith("vault://")
    assert client.get("/api/v1/platform/identity/mfa").status_code == 200


def test_custom_role_temp_access_permission_audit():
    login_as("operator")
    code = f"role.{uuid.uuid4().hex[:8]}"
    role = client.post(
        "/api/v1/platform/rbac/roles",
        json={"code": code, "name": "Temp Shop Lead", "permissions": "platform.read,logistics.read"},
    )
    assert role.status_code == 201, role.text
    ends = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    temp = client.post(
        "/api/v1/platform/rbac/temporary-access",
        json={
            "username": "viewer",
            "permissions": "logistics.manage",
            "reason": "weekend coverage",
            "ends_at": ends,
        },
    )
    assert temp.status_code == 201, temp.text
    audits = client.get("/api/v1/platform/rbac/permission-audits")
    assert audits.status_code == 200
    assert len(audits.json()) >= 1
    matrix = client.get("/api/v1/platform/rbac/matrix")
    assert matrix.status_code == 200
    assert "Operator" in matrix.json()["roles"]


def test_generic_workflow_engine():
    login_as("operator")
    defs = client.get("/api/v1/platform/workflows/definitions")
    assert defs.status_code == 200
    assert any(d["code"] == "enterprise.default" for d in defs.json())
    entity_id = f"entity-{uuid.uuid4().hex[:8]}"
    started = client.post(
        "/api/v1/platform/workflows/instances",
        json={
            "definition_code": "enterprise.default",
            "entity_type": "work_order",
            "entity_id": entity_id,
            "assigned_to": "operator",
        },
    )
    assert started.status_code == 201, started.text
    instance_id = started.json()["id"]
    assert started.json()["current_state"] == "draft"

    to_assigned = client.post(
        f"/api/v1/platform/workflows/instances/{instance_id}/transition",
        json={"to_state": "assigned", "comment": "dispatch"},
    )
    assert to_assigned.status_code == 200, to_assigned.text
    assert to_assigned.json()["current_state"] == "assigned"

    bad = client.post(
        f"/api/v1/platform/workflows/instances/{instance_id}/transition",
        json={"to_state": "released"},
    )
    assert bad.status_code == 400

    for state in ("in_progress", "inspection", "released"):
        r = client.post(
            f"/api/v1/platform/workflows/instances/{instance_id}/transition",
            json={"to_state": state},
        )
        assert r.status_code == 200, r.text

    logs = client.get(f"/api/v1/platform/workflows/instances/{instance_id}/logs")
    assert logs.status_code == 200
    assert len(logs.json()) >= 5


def test_notifications_files_search_settings():
    login_as("operator")
    notif = client.post(
        "/api/v1/platform/notifications",
        json={
            "recipient": "operator",
            "channel": "in_app",
            "event_type": "workflow.assigned",
            "title": "Assigned",
            "body": "Work assigned",
        },
    )
    assert notif.status_code == 201, notif.text
    nid = notif.json()["id"]
    assert client.post(f"/api/v1/platform/notifications/{nid}/sent").status_code == 200
    assert client.post(f"/api/v1/platform/notifications/{nid}/read").status_code == 200

    entity_id = f"pub-{uuid.uuid4().hex[:8]}"
    filename = f"AMM-{uuid.uuid4().hex[:6]}.pdf"
    file_res = client.post(
        "/api/v1/platform/files",
        json={
            "filename": filename,
            "content_type": "application/pdf",
            "file_class": "publication",
            "storage_uri": f"s3://mercury/pubs/{filename}",
            "sha256": "a" * 64,
            "size_bytes": 1024,
            "entity_type": "publication",
            "entity_id": entity_id,
            "virus_scan_status": "clean",
        },
    )
    assert file_res.status_code == 201, file_res.text
    assert file_res.json()["version"] == 1
    file_v2 = client.post(
        "/api/v1/platform/files",
        json={
            "filename": filename,
            "content_type": "application/pdf",
            "file_class": "publication",
            "storage_uri": f"s3://mercury/pubs/{filename}-v2",
            "sha256": "b" * 64,
            "size_bytes": 2048,
            "entity_type": "publication",
            "entity_id": entity_id,
        },
    )
    assert file_v2.status_code == 201
    assert file_v2.json()["version"] == 2

    idx = client.post(
        "/api/v1/platform/search/index",
        json={
            "doc_type": "aircraft",
            "entity_id": f"ac-{uuid.uuid4().hex[:6]}",
            "title": "N123ME Boeing 737",
            "body": "Narrow body fleet aircraft",
            "keywords": "b737,narrowbody",
        },
    )
    assert idx.status_code == 201, idx.text
    search = client.get("/api/v1/platform/search", params={"q": "737"})
    assert search.status_code == 200
    assert search.json()["total"] >= 1

    setting = client.put(
        "/api/v1/platform/settings",
        json={"key": "timezone", "value": "UTC", "category": "regional"},
    )
    assert setting.status_code == 200, setting.text
    assert setting.json()["value"] == "UTC"

    flag = client.put(
        "/api/v1/platform/feature-flags/org",
        json={"flag_code": "platform.mfa_required", "enabled": True},
    )
    assert flag.status_code == 200, flag.text
    assert flag.json()["enabled"] == "true"
