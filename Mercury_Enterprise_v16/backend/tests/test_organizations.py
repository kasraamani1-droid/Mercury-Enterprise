"""Sprint 5 — Enterprise Organizations & Multi-Tenancy tests."""

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


def test_seeded_hierarchy_visible_to_admin():
    login_as("admin")
    companies = client.get("/api/v1/companies")
    assert companies.status_code == 200
    assert any(item["code"] == "MAG" for item in companies.json())

    orgs = client.get("/api/v1/organizations")
    assert orgs.status_code == 200
    org_ids = {item["organization_id"] for item in orgs.json()}
    assert "org-aviation-east" in org_ids
    assert "org-aviation-west" in org_ids

    sites = client.get("/api/v1/organizations/org-aviation-east/sites")
    assert sites.status_code == 200
    site_ids = {item["site_id"] for item in sites.json()}
    assert "site-cyul" in site_ids
    assert "site-cyyz" in site_ids


def test_operator_cannot_switch_to_unassigned_organization():
    login_as("operator")
    context = client.get("/api/v1/auth/context")
    assert context.status_code == 200
    payload = context.json()
    allowed = {item["organization_id"] for item in payload["organizations"]}
    assert "org-aviation-east" in allowed
    assert "org-aviation-west" not in allowed

    denied = client.post(
        "/api/v1/auth/context",
        json={"organization_id": "org-aviation-west", "site_id": "site-cyvr"},
    )
    assert denied.status_code == 403


def test_admin_can_switch_organization():
    login_as("admin")
    updated = client.post(
        "/api/v1/auth/context",
        json={"organization_id": "org-aviation-west", "site_id": "site-cyvr"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["organization"]["organization_id"] == "org-aviation-west"
    assert body["site"]["site_id"] == "site-cyvr"


def test_org_isolation_on_sites_list():
    login_as("operator")
    forbidden = client.get("/api/v1/organizations/org-aviation-west/sites")
    assert forbidden.status_code == 403


def test_create_department_and_team_requires_admin():
    suffix = uuid.uuid4().hex[:8].upper()
    login_as("operator")
    denied = client.post(
        "/api/v1/departments",
        json={
            "organization_id": "org-aviation-east",
            "name": f"Security East {suffix}",
            "code": f"S{suffix[:6]}",
            "site_id": "site-cyul",
        },
    )
    assert denied.status_code == 403

    login_as("admin")
    created = client.post(
        "/api/v1/departments",
        json={
            "organization_id": "org-aviation-east",
            "name": f"Security East {suffix}",
            "code": f"S{suffix[:6]}",
            "site_id": "site-cyul",
        },
    )
    assert created.status_code == 201
    dept_id = created.json()["id"]

    team = client.post(
        "/api/v1/teams",
        json={
            "organization_id": "org-aviation-east",
            "department_id": dept_id,
            "name": f"Perimeter Team {suffix}",
            "code": f"P{suffix[:6]}",
        },
    )
    assert team.status_code == 201
    assert team.json()["code"] == f"P{suffix[:6]}"


def test_membership_create_and_org_me():
    suffix = uuid.uuid4().hex[:8]
    username = f"east{suffix}"
    password = "enterprise-user-password"
    login_as("admin")
    user = client.post(
        "/api/v1/org/users",
        json={
            "username": username,
            "password": password,
            "display_name": "East Only",
        },
    )
    assert user.status_code == 201

    membership = client.post(
        "/api/v1/memberships",
        json={
            "username": username,
            "organization_id": "org-aviation-east",
            "role": "Viewer",
            "site_id": "site-cyul",
        },
    )
    assert membership.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"operator": username, "password": password},
    )
    assert login.status_code == 200
    me = client.get("/api/v1/org/me")
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == username
    assert any(item["organization_id"] == "org-aviation-east" for item in body["memberships"])

    denied = client.post(
        "/api/v1/auth/context",
        json={"organization_id": "org-aviation-west"},
    )
    assert denied.status_code == 403


def test_list_departments_scoped_to_session_org():
    login_as("operator")
    response = client.get("/api/v1/departments")
    assert response.status_code == 200
    assert all(item["organization_id"] == "org-aviation-east" for item in response.json())


def test_membership_cannot_assign_administrator_role():
    login_as("admin")
    denied = client.post(
        "/api/v1/memberships",
        json={
            "username": "viewer",
            "organization_id": "org-aviation-east",
            "role": "Administrator",
            "site_id": "site-cyul",
        },
    )
    assert denied.status_code == 400


def test_membership_does_not_elevate_to_platform_admin():
    suffix = uuid.uuid4().hex[:8]
    username = f"escal{suffix}"
    password = "enterprise-user-password"
    login_as("admin")
    assert client.post(
        "/api/v1/org/users",
        json={"username": username, "password": password, "display_name": "Escalation Probe"},
    ).status_code == 201
    # Highest allowed membership role is Operator — still must not unlock /admin.
    assert (
        client.post(
            "/api/v1/memberships",
            json={
                "username": username,
                "organization_id": "org-aviation-east",
                "role": "Operator",
                "site_id": "site-cyul",
            },
        ).status_code
        == 201
    )
    login = client.post("/api/v1/auth/login", json={"operator": username, "password": password})
    assert login.status_code == 200
    assert login.json()["role"] == "Operator"
    admin_probe = client.get("/admin/system")
    assert admin_probe.status_code == 403


def test_user_without_membership_cannot_login_session():
    suffix = uuid.uuid4().hex[:8]
    username = f"nomem{suffix}"
    password = "enterprise-user-password"
    login_as("admin")
    assert client.post(
        "/api/v1/org/users",
        json={"username": username, "password": password},
    ).status_code == 201
    # Directory account exists, but no org membership → session creation denied.
    denied = client.post("/api/v1/auth/login", json={"operator": username, "password": password})
    assert denied.status_code == 403


def test_operator_membership_list_is_self_only():
    login_as("operator")
    own = client.get("/api/v1/memberships")
    assert own.status_code == 200
    assert all(item["username"] == "operator" for item in own.json())
    other = client.get("/api/v1/memberships", params={"username": "viewer"})
    assert other.status_code == 403


def test_duplicate_membership_rejected():
    login_as("admin")
    payload = {
        "username": "viewer",
        "organization_id": "org-aviation-east",
        "role": "Viewer",
        "site_id": "site-cyul",
    }
    first = client.post("/api/v1/memberships", json=payload)
    # May already exist from seed; either 201 or 409 is acceptable for first call.
    assert first.status_code in (201, 409)
    second = client.post("/api/v1/memberships", json=payload)
    assert second.status_code == 409
