"""RC1 Blocker 03 — durable, tenant-scoped approval persistence."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import ApprovalRequest

client = TestClient(app)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _logout():
    client.post("/api/v1/auth/logout")


def _login(operator: str = "operator"):
    response = client.post(
        "/api/v1/auth/login",
        json={"operator": operator, "password": TEST_AUTH_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_approval_persisted_in_sql():
    _logout()
    _login("operator")
    created = client.post(
        "/api/v1/approvals",
        json={"action": "incident.resolve", "target_id": "INC-PERSIST", "reason": "durable"},
    )
    assert created.status_code == 200, created.text
    approval_id = created.json()["approval_id"]
    assert created.json()["organization_id"]
    assert created.json()["site_id"]

    db = SessionLocal()
    try:
        row = db.get(ApprovalRequest, approval_id)
        assert row is not None
        assert row.action == "incident.resolve"
        assert row.target_id == "INC-PERSIST"
        assert row.status == "pending"
        assert row.requested_by == "operator"
        assert row.consumed is False
    finally:
        db.close()


def test_approvals_survive_restart_simulation():
    """Rows remain readable from a fresh DB session (process restart stand-in)."""
    _logout()
    _login("operator")
    created = client.post(
        "/api/v1/approvals",
        json={"action": "incident.resolve", "target_id": "INC-RESTART", "reason": "restart"},
    )
    assert created.status_code == 200
    approval_id = created.json()["approval_id"]
    org_id = created.json()["organization_id"]
    site_id = created.json()["site_id"]

    # New SessionLocal mimics a new process reading the same database file.
    db = SessionLocal()
    try:
        row = db.scalar(select(ApprovalRequest).where(ApprovalRequest.id == approval_id))
        assert row is not None
        assert row.organization_id == org_id
        assert row.site_id == site_id
        assert row.status == "pending"
    finally:
        db.close()

    _login("reviewer")
    listing = client.get("/api/v1/approvals", params={"status_filter": "pending"})
    assert listing.status_code == 200
    assert any(item["approval_id"] == approval_id for item in listing.json())


def test_approval_history_auditable_request_approve_consume():
    _logout()
    _login("operator")
    incident = client.post(
        "/api/v1/incidents",
        json={"title": "Approval persist audit", "severity": "medium", "summary": "rb-03"},
    )
    assert incident.status_code == 201
    incident_id = incident.json()["id"]

    req = client.post(
        "/api/v1/approvals",
        json={"action": "incident.resolve", "target_id": incident_id, "reason": "audit trail"},
    )
    assert req.status_code == 200
    approval_id = req.json()["approval_id"]

    _login("reviewer")
    approved = client.post(f"/api/v1/approvals/{approval_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    _login("operator")
    resolved = client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "resolved", "approval_id": approval_id},
    )
    assert resolved.status_code == 200

    db = SessionLocal()
    try:
        row = db.get(ApprovalRequest, approval_id)
        assert row is not None
        assert row.status == "approved"
        assert row.consumed is True
        assert row.reviewed_by == "reviewer"
        assert row.reviewed_at is not None
    finally:
        db.close()

    _login("reviewer")
    actions = {row["action"] for row in client.get("/api/v1/audit", params={"limit": 200}).json()}
    assert "approval.request" in actions
    assert "approval.approve" in actions
    assert "approval.consume" in actions


def test_approval_tenant_isolation_list_and_approve():
    _logout()
    _login("operator")
    east = client.post(
        "/api/v1/approvals",
        json={"action": "incident.resolve", "target_id": "INC-EAST", "reason": "east"},
    )
    assert east.status_code == 200
    east_id = east.json()["approval_id"]
    east_org = east.json()["organization_id"]
    assert east_org == "org-aviation-east"

    # Insert a west-tenant approval directly (operator cannot create under west via API).
    west_id = f"approval-west-{secrets.token_urlsafe(8)}"
    db = SessionLocal()
    try:
        west_row = ApprovalRequest(
            id=west_id,
            action="incident.resolve",
            target_id="INC-WEST",
            reason="west",
            status="pending",
            requested_by="operator",
            requested_role="Operator",
            organization_id="org-aviation-west",
            site_id="site-cyvr",
            created_at=_utcnow(),
            consumed=False,
        )
        db.add(west_row)
        db.commit()
    finally:
        db.close()

    _login("reviewer")
    listing = client.get("/api/v1/approvals", params={"status_filter": "pending", "limit": 500})
    assert listing.status_code == 200
    ids = {item["approval_id"] for item in listing.json()}
    assert east_id in ids
    assert west_id not in ids
    assert all(item["organization_id"] == "org-aviation-east" for item in listing.json())

    denied = client.post(f"/api/v1/approvals/{west_id}/approve")
    assert denied.status_code == 404

    # Admin on west context can see and approve the west row.
    _login("admin")
    switched = client.post(
        "/api/v1/auth/context",
        json={"organization_id": "org-aviation-west", "site_id": "site-cyvr"},
    )
    assert switched.status_code == 200, switched.text
    west_list = client.get("/api/v1/approvals", params={"status_filter": "pending", "limit": 500})
    assert west_list.status_code == 200
    west_ids = {item["approval_id"] for item in west_list.json()}
    assert west_id in west_ids
    assert east_id not in west_ids

    approved = client.post(f"/api/v1/approvals/{west_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_approval_permissions_enforced():
    _logout()
    _login("viewer")
    denied_request = client.post(
        "/api/v1/approvals",
        json={"action": "incident.resolve", "target_id": "x", "reason": "no"},
    )
    assert denied_request.status_code == 403
    denied_list = client.get("/api/v1/approvals")
    assert denied_list.status_code == 403

    _login("operator")
    created = client.post(
        "/api/v1/approvals",
        json={"action": "incident.resolve", "target_id": "INC-PERM", "reason": "ok"},
    )
    assert created.status_code == 200
    approval_id = created.json()["approval_id"]
    assert client.get("/api/v1/approvals").status_code == 403
    assert client.post(f"/api/v1/approvals/{approval_id}/approve").status_code == 403

    _login("reviewer")
    assert client.get("/api/v1/approvals").status_code == 200
    assert client.post(f"/api/v1/approvals/{approval_id}/approve").status_code == 200


def test_cross_tenant_consume_rejected():
    _logout()
    _login("operator")
    incident = client.post(
        "/api/v1/incidents",
        json={"title": "Cross tenant consume", "severity": "low", "summary": "rb-03"},
    )
    assert incident.status_code == 201
    incident_id = incident.json()["id"]

    foreign_id = f"approval-foreign-{secrets.token_urlsafe(8)}"
    db = SessionLocal()
    try:
        foreign = ApprovalRequest(
            id=foreign_id,
            action="incident.resolve",
            target_id=incident_id,
            reason="foreign",
            status="approved",
            requested_by="operator",
            requested_role="Operator",
            organization_id="org-aviation-west",
            site_id="site-cyvr",
            reviewed_by="admin",
            created_at=_utcnow(),
            consumed=False,
        )
        db.add(foreign)
        db.commit()
    finally:
        db.close()

    _login("operator")
    rejected = client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "resolved", "approval_id": foreign_id},
    )
    assert rejected.status_code == 404


def test_approval_survives_logout_and_relogin():
    _logout()
    _login("operator")
    created = client.post(
        "/api/v1/approvals",
        json={"action": "incident.resolve", "target_id": "INC-RELOGIN", "reason": "session cycle"},
    )
    assert created.status_code == 200
    approval_id = created.json()["approval_id"]

    _logout()
    assert client.get("/api/v1/approvals").status_code == 401

    _login("reviewer")
    listing = client.get("/api/v1/approvals", params={"limit": 500})
    assert listing.status_code == 200
    assert any(item["approval_id"] == approval_id for item in listing.json())


def test_approval_history_lists_consumed_rows():
    _logout()
    _login("operator")
    incident = client.post(
        "/api/v1/incidents",
        json={"title": "Approval history", "severity": "low", "summary": "rb-03"},
    )
    assert incident.status_code == 201
    incident_id = incident.json()["id"]
    req = client.post(
        "/api/v1/approvals",
        json={"action": "incident.resolve", "target_id": incident_id, "reason": "history"},
    )
    assert req.status_code == 200
    approval_id = req.json()["approval_id"]

    _login("reviewer")
    assert client.post(f"/api/v1/approvals/{approval_id}/approve").status_code == 200
    _login("operator")
    assert client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "resolved", "approval_id": approval_id},
    ).status_code == 200

    _login("reviewer")
    listing = client.get("/api/v1/approvals", params={"limit": 500})
    assert listing.status_code == 200
    row = next(item for item in listing.json() if item["approval_id"] == approval_id)
    assert row["status"] == "approved"
    assert row["consumed"] is True
    assert row["reviewed_by"] == "reviewer"


def test_double_approve_and_consume_conflict():
    _logout()
    _login("operator")
    incident = client.post(
        "/api/v1/incidents",
        json={"title": "Approval conflict", "severity": "low", "summary": "rb-03"},
    )
    incident_id = incident.json()["id"]
    req = client.post(
        "/api/v1/approvals",
        json={"action": "incident.resolve", "target_id": incident_id, "reason": "conflict"},
    )
    approval_id = req.json()["approval_id"]

    _login("reviewer")
    assert client.post(f"/api/v1/approvals/{approval_id}/approve").status_code == 200
    again = client.post(f"/api/v1/approvals/{approval_id}/approve")
    assert again.status_code == 409

    _login("operator")
    first = client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "resolved", "approval_id": approval_id},
    )
    assert first.status_code == 200
    second = client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "closed", "approval_id": approval_id},
    )
    assert second.status_code == 409


def test_consume_error_handling():
    _logout()
    _login("operator")
    incident = client.post(
        "/api/v1/incidents",
        json={"title": "Approval errors", "severity": "low", "summary": "rb-03"},
    )
    incident_id = incident.json()["id"]

    missing = client.patch(f"/api/v1/incidents/{incident_id}/status", json={"status": "resolved"})
    assert missing.status_code == 400

    pending = client.post(
        "/api/v1/approvals",
        json={"action": "incident.resolve", "target_id": incident_id, "reason": "pending"},
    )
    pending_id = pending.json()["approval_id"]
    still_pending = client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "resolved", "approval_id": pending_id},
    )
    assert still_pending.status_code == 409

    mismatch = client.post(
        "/api/v1/approvals",
        json={"action": "other.action", "target_id": incident_id, "reason": "mismatch"},
    )
    mismatch_id = mismatch.json()["approval_id"]
    _login("reviewer")
    assert client.post(f"/api/v1/approvals/{mismatch_id}/approve").status_code == 200
    unknown = client.post("/api/v1/approvals/does-not-exist/approve")
    assert unknown.status_code == 404

    _login("operator")
    wrong_action = client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "resolved", "approval_id": mismatch_id},
    )
    assert wrong_action.status_code == 409
