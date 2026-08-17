"""EPIC-009 security regression: sessions, API key, tenant isolation, cookie Secure."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app
from app.security.sessions import MemorySessionBackend, SessionStore

client = TestClient(app)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _logout():
    client.post("/api/v1/auth/logout")


def _login(operator: str = "operator"):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text
    return response


def test_memory_session_store_roundtrip():
    store = SessionStore(backend=MemorySessionBackend())
    assert store.backend_name == "memory"
    expires = _utcnow() + timedelta(hours=1)
    store.save(
        "sid-test-1",
        {
            "operator": "operator",
            "role": "Operator",
            "organization_id": "org-aviation-east",
            "site_id": "site-cyul",
            "created_at": _utcnow(),
            "expires_at": expires,
        },
    )
    got = store.get("sid-test-1")
    assert got is not None
    assert got["operator"] == "operator"
    assert store.count() == 1
    store.delete("sid-test-1")
    assert store.get("sid-test-1") is None


def test_login_logout_uses_session_store():
    _logout()
    _login("operator")
    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json()["authenticated"] is True
    _logout()
    assert client.get("/api/v1/auth/session").json()["authenticated"] is False


def test_api_key_auth_when_configured(monkeypatch):
    _logout()
    object.__setattr__(settings, "api_key", "epic009-test-api-key-value")
    try:
        denied = client.get("/api/v1/fleet/aircraft")
        assert denied.status_code == 401

        bad = client.get("/api/v1/fleet/aircraft", headers={"X-API-Key": "wrong-key"})
        assert bad.status_code == 401
        assert "API key" in bad.json()["detail"]

        ok = client.get("/api/v1/fleet/aircraft", headers={"X-API-Key": "epic009-test-api-key-value"})
        assert ok.status_code == 200

        bearer = client.get(
            "/api/v1/dashboard/summary",
            headers={"Authorization": "Bearer epic009-test-api-key-value"},
        )
        assert bearer.status_code == 200
    finally:
        object.__setattr__(settings, "api_key", "")


def test_api_key_cannot_switch_org_context(monkeypatch):
    _logout()
    object.__setattr__(settings, "api_key", "epic009-test-api-key-value")
    try:
        response = client.post(
            "/api/v1/auth/context",
            headers={"X-API-Key": "epic009-test-api-key-value"},
            json={"organization_id": "org-aviation-west"},
        )
        assert response.status_code == 400
    finally:
        object.__setattr__(settings, "api_key", "")


def test_api_key_tenant_isolation_west_denied():
    """Machine principal is scoped to configured org only (east by default)."""
    _logout()
    object.__setattr__(settings, "api_key", "epic009-test-api-key-value")
    try:
        denied = client.get(
            "/api/v1/fleet/aircraft",
            headers={"X-API-Key": "epic009-test-api-key-value"},
            params={"organization_id": "org-aviation-west"},
        )
        assert denied.status_code == 403
    finally:
        object.__setattr__(settings, "api_key", "")


def test_production_forces_secure_session_cookie():
    class _Probe:
        environment = "production"
        https_enabled = False
        session_cookie_secure = False
        auth_password = "production-grade-password-99"
        jwt_secret = "j" * 32
        cookie_secret = "c" * 32
        domain = ""
        letsencrypt_email = ""

        def validate_for_startup(self):
            Settings.validate_for_startup(self)  # type: ignore[arg-type]

    try:
        _Probe().validate_for_startup()
        raise AssertionError("expected RuntimeError for insecure cookie")
    except RuntimeError as exc:
        assert "Secure" in str(exc) or "cookie" in str(exc).lower()


def test_tenant_isolation_fleet_work_orders_marketplace_twin_logistics():
    """Operator (east-only membership) cannot read west-scoped tenant resources."""
    _logout()
    _login("operator")

    west = "org-aviation-west"
    cases = [
        ("/api/v1/fleet/aircraft", {"organization_id": west}),
        ("/api/v1/work-orders/packages", {"organization_id": west}),
        ("/api/v1/work-orders/orders", {"organization_id": west}),
        ("/api/v1/marketplace/sellers", {"organization_id": west}),
        ("/api/v1/marketplace/products", {"organization_id": west}),
        ("/api/v1/twin/twins", {"organization_id": west}),
        ("/api/v1/logistics/parts", {"organization_id": west}),
        ("/api/v1/logistics/warehouses", {"organization_id": west}),
        ("/api/v1/planning/programs", {"organization_id": west}),
    ]
    for path, params in cases:
        response = client.get(path, params=params)
        assert response.status_code == 403, f"{path} expected 403 got {response.status_code}: {response.text}"


def test_tenant_isolation_operator_cannot_switch_to_west():
    _logout()
    _login("operator")
    denied = client.post(
        "/api/v1/auth/context",
        json={"organization_id": "org-aviation-west", "site_id": "site-cyvr"},
    )
    assert denied.status_code == 403


def test_tenant_isolation_admin_can_read_west_after_switch():
    _logout()
    _login("admin")
    switched = client.post(
        "/api/v1/auth/context",
        json={"organization_id": "org-aviation-west", "site_id": "site-cyvr"},
    )
    assert switched.status_code == 200, switched.text
    assert switched.json()["organization"]["organization_id"] == "org-aviation-west"
    fleet = client.get("/api/v1/fleet/aircraft", params={"organization_id": "org-aviation-west"})
    assert fleet.status_code == 200
