"""EPIC-003 backend completion: authz overlays, registration CRUD, marketplace scope, OpenAPI."""

from __future__ import annotations

from datetime import datetime, timedelta

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database import SessionLocal
from app.main import app
from app.publications.storage import LocalFilesystemStorage, normalize_storage
from app.platform.permission_service import PermissionService

client = TestClient(app)


def _logout():
    client.post("/api/v1/auth/logout")


def _login(operator: str = "admin"):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text
    return response


def test_openapi_program_tags_have_descriptions():
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    tags = {t["name"]: t for t in spec.json().get("tags", [])}
    for name in ("marketplace", "network", "twin", "plugins", "event-fabric"):
        assert name in tags
        assert (tags[name].get("description") or "").strip()
    paths = spec.json().get("paths", {})
    assert "/api/v1/fleet/registrations/{registration_id}" in paths
    assert "patch" in paths["/api/v1/fleet/registrations/{registration_id}"]


def test_temp_access_grants_marketplace_manage_to_viewer():
    _logout()
    _login("admin")
    ends = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    grant = client.post(
        "/api/v1/platform/rbac/temporary-access",
        json={
            "username": "viewer",
            "permissions": "marketplace.manage",
            "ends_at": ends,
            "reason": "epic003-temp",
        },
    )
    assert grant.status_code == 201, grant.text

    _logout()
    _login("viewer")
    sellers = client.get("/api/v1/marketplace/sellers")
    assert sellers.status_code == 200
    created = client.post(
        "/api/v1/marketplace/sellers",
        json={
            "seller_type": "consultant",
            "legal_name": f"EPIC003 Temp Seller {datetime.utcnow().strftime('%H%M%S%f')}",
            "country": "CA",
        },
    )
    assert created.status_code == 201, created.text


def test_marketplace_cart_quote_org_isolation():
    _logout()
    _login("operator")
    denied_cart = client.get("/api/v1/marketplace/cart", params={"organization_id": "org-aviation-west"})
    assert denied_cart.status_code == 403
    denied_quotes = client.get("/api/v1/marketplace/quotes", params={"organization_id": "org-aviation-west"})
    assert denied_quotes.status_code == 403
    denied_orders = client.get("/api/v1/marketplace/orders", params={"organization_id": "org-aviation-west"})
    assert denied_orders.status_code == 403


def test_registration_get_and_patch_notes():
    _logout()
    _login("admin")
    aircraft = client.get("/api/v1/fleet/aircraft").json()
    assert aircraft
    aircraft_id = aircraft[0]["id"]
    mark = f"T{datetime.utcnow().strftime('%H%M%S')}"
    created = client.post(
        "/api/v1/fleet/registrations",
        json={
            "aircraft_id": aircraft_id,
            "registration_mark": mark,
            "country": "CA",
            "make_current": False,
            "notes": "epic003",
        },
    )
    assert created.status_code == 201, created.text
    reg_id = created.json()["id"]
    got = client.get(f"/api/v1/fleet/registrations/{reg_id}")
    assert got.status_code == 200
    assert got.json()["registration_mark"] == mark.upper()

    patched = client.patch(
        f"/api/v1/fleet/registrations/{reg_id}",
        json={"notes": "updated-notes", "country": "US"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["notes"] == "updated-notes"
    assert patched.json()["country"] == "US"
    assert patched.json()["is_current"] is False


def test_publications_local_filesystem_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("MERCURY_PUBLICATIONS_STORAGE_ROOT", str(tmp_path))
    object.__setattr__(settings, "publications_storage_root", str(tmp_path))
    ref = normalize_storage(kind="local_filesystem", object_key="manual-ref-1", content_type="application/pdf")
    assert ref.kind == "local_filesystem"
    assert ref.object_key == "manual-ref-1"
    assert ref.uri.startswith("file:")
    resolved = LocalFilesystemStorage().resolve(ref)
    assert resolved.uri.startswith("file:")


def test_permission_service_allows_temp_overlay():
    _logout()
    _login("admin")
    ends = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    grant = client.post(
        "/api/v1/platform/rbac/temporary-access",
        json={
            "username": "viewer",
            "permissions": "fleet.manage",
            "ends_at": ends,
            "reason": "epic003-fleet",
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
            required=("fleet.manage",),
        )
        assert not svc.allows(
            username="viewer",
            role="Viewer",
            organization_id="org-aviation-east",
            required=("admin.system",),
        )
    finally:
        db.close()
