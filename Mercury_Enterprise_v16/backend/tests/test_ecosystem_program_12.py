"""Program 12 — Aviation Digital Ecosystem + Mercury Connect tests."""

from __future__ import annotations

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    r = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert r.status_code == 200
    return r.json()


def test_ecosystem_catalog_seeded():
    login_as("operator")
    overview = client.get("/api/v1/ecosystem/overview")
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["ecosystems"] >= 11
    assert body["capabilities"] >= 50
    assert body["enrollments"] >= 1
    defs = client.get("/api/v1/ecosystem/definitions")
    codes = {d["code"] for d in defs.json()}
    for required in (
        "airline",
        "business_aviation",
        "mro",
        "camo",
        "oem",
        "supplier",
        "repair_station",
        "authority",
        "training",
        "careers",
        "marketplace",
    ):
        assert required in codes
    mro = client.get("/api/v1/ecosystem/definitions/mro")
    assert mro.status_code == 200
    assert len(mro.json()["capabilities"]) >= 8
    auth = client.get("/api/v1/ecosystem/definitions/authority")
    assert "regulatory" in auth.json()["ecosystem"]["description"].lower() or "approval" in auth.json()["ecosystem"]["description"].lower()


def test_enrollments_and_rbac():
    login_as("viewer")
    assert client.get("/api/v1/ecosystem/overview").status_code == 200
    assert (
        client.post(
            "/api/v1/ecosystem/enrollments",
            json={"ecosystem_code": "supplier", "role_label": "Nope"},
        ).status_code
        == 403
    )
    login_as("operator")
    # already enrolled in airline — enroll supplier
    r = client.post(
        "/api/v1/ecosystem/enrollments",
        json={"ecosystem_code": "supplier", "role_label": "Parts supplier"},
    )
    assert r.status_code in {201, 409}, r.text
    listed = client.get("/api/v1/ecosystem/enrollments")
    assert listed.status_code == 200
    assert any(e["ecosystem_code"] == "airline" for e in listed.json())


def test_connect_catalog_and_bindings():
    login_as("operator")
    overview = client.get("/api/v1/connect/overview")
    assert overview.status_code == 200, overview.text
    assert overview.json()["connectors"] >= 10
    connectors = client.get("/api/v1/connect/connectors", params={"category": "identity"})
    assert connectors.status_code == 200
    codes = {c["code"] for c in connectors.json()}
    assert "identity.oidc" in codes
    assert "identity.okta" in codes
    bindings = client.get("/api/v1/connect/bindings")
    assert bindings.status_code == 200
    assert len(bindings.json()) >= 1
    assert all(b.get("config_ref", "").startswith("vault://") or b.get("config_ref") == "" for b in bindings.json())
    created = client.post(
        "/api/v1/connect/bindings",
        json={
            "connector_code": "courier.generic",
            "display_name": "Demo Courier",
            "config_ref": "vault://connect/org-aviation-east/courier.generic",
        },
    )
    assert created.status_code in {201, 409}, created.text


def test_tenant_isolation_ecosystem():
    login_as("operator")
    assert (
        client.get("/api/v1/ecosystem/enrollments", params={"organization_id": "org-aviation-west"}).status_code
        == 403
    )
    assert (
        client.get("/api/v1/connect/bindings", params={"organization_id": "org-aviation-west"}).status_code
        == 403
    )
