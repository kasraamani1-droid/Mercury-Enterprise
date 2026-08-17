"""AEOS architecture standardization — marketplace/OEM/authority + platform integrations."""

from __future__ import annotations

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app
from app.platform.permission_service import PermissionService
from app.platform.workflow_bridge import JOB_CARD_WORKFLOW_CODE, WorkflowBridge
from app.database import SessionLocal

client = TestClient(app)


def login_as(operator: str):
    r = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert r.status_code == 200
    return r.json()


def test_marketplace_oem_authority_seeded():
    login_as("operator")
    listings = client.get("/api/v1/marketplace/listings")
    assert listings.status_code == 200, listings.text
    types = {row["listing_type"] for row in listings.json()}
    assert "parts" in types
    assert "publications" in types

    oems = client.get("/api/v1/oem/manufacturers")
    assert oems.status_code == 200
    codes = {m["code"] for m in oems.json()}
    assert "boeing" in codes and "airbus" in codes and "bombardier" in codes

    authorities = client.get("/api/v1/authority/bodies")
    assert authorities.status_code == 200
    acodes = {a["code"] for a in authorities.json()}
    assert "faa" in acodes and "easa" in acodes and "tc" in acodes
    assert all("Not certified" in a["disclaimer"] or "regulatory" in a["disclaimer"].lower() for a in authorities.json())


def test_integrations_registry():
    login_as("operator")
    integ = client.get("/api/v1/platform/integrations", params={"category": "sso"})
    assert integ.status_code == 200
    codes = {i["code"] for i in integ.json()}
    assert "sso.oidc" in codes
    assert "sso.okta" in codes
    health = client.get("/api/v1/platform/integrations/health")
    assert health.status_code == 200
    assert "integrations" in health.json()


def test_job_card_workflow_definition_seeded():
    login_as("operator")
    defs = client.get("/api/v1/platform/workflows/definitions")
    assert defs.status_code == 200
    codes = {d["code"] for d in defs.json()}
    assert "enterprise.default" in codes
    assert JOB_CARD_WORKFLOW_CODE in codes


def test_workflow_bridge_allows_assigned_from_draft():
    db = SessionLocal()
    try:
        bridge = WorkflowBridge(db)
        bridge.ensure_job_card_definition("org-aviation-east")
        allowed = bridge.allowed_transitions("org-aviation-east", JOB_CARD_WORKFLOW_CODE, "draft")
        assert "assigned" in allowed
        assert "waiting_inspection" not in allowed
    finally:
        db.close()


def test_permission_service_temp_overlay():
    login_as("operator")
    ends = __import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(hours=1)
    grant = client.post(
        "/api/v1/platform/rbac/temporary-access",
        json={
            "username": "viewer",
            "permissions": "marketplace.manage",
            "reason": "aeos test",
            "ends_at": ends.isoformat(),
        },
    )
    assert grant.status_code == 201, grant.text
    db = SessionLocal()
    try:
        svc = PermissionService(db)
        assert svc.allows(
            username="viewer",
            role="Viewer",
            organization_id="org-aviation-east",
            required=("marketplace.manage",),
        )
    finally:
        db.close()
