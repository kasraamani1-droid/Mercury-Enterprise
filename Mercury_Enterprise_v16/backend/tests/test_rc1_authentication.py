"""RC1 Blocker 01 — authentication, session, RBAC, tenant, audit, OpenAPI."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.security.rate_limit import rate_limiter
from app.security.sessions import MemorySessionBackend, SessionStore, session_store

client = TestClient(app)
PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _logout():
    client.post("/api/v1/auth/logout")


def _login(operator: str = "operator", password: str = TEST_AUTH_PASSWORD):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": password})
    assert response.status_code == 200, response.text
    return response


def test_login_success_sets_httponly_cookie_without_jwt():
    _logout()
    response = _login("operator")
    body = response.json()
    assert body["authenticated"] is True
    assert body["operator"] == "operator"
    assert body["role"] == "Operator"
    assert "expires_at" in body
    assert "password" not in body
    assert "password_hash" not in body
    assert "access_token" not in body
    assert "refresh_token" not in body
    assert "token" not in body
    assert "jwt" not in str(body).lower()
    cookie = (response.headers.get("set-cookie") or "").lower()
    assert settings.session_cookie_name.lower() in cookie
    assert "httponly" in cookie


def test_login_wrong_password_is_generic_401():
    _logout()
    response = client.post(
        "/api/v1/auth/login",
        json={"operator": "operator", "password": "definitely-not-the-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
    assert "operator" not in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


def test_login_unknown_user_is_generic_401():
    _logout()
    response = client.post(
        "/api/v1/auth/login",
        json={"operator": "no-such-operator-xyz", "password": "enterprise-user-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_empty_payload_is_rejected():
    _logout()
    response = client.post("/api/v1/auth/login", json={"operator": "", "password": ""})
    assert response.status_code in {401, 422}


def test_logout_is_idempotent_without_session():
    _logout()
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    assert client.get("/api/v1/auth/session").json()["authenticated"] is False


def test_logout_invalidates_session_and_protected_routes():
    _login("operator")
    assert client.get("/api/v1/incidents").status_code == 200
    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert logout.json()["authenticated"] is False
    assert client.get("/api/v1/auth/session").json()["authenticated"] is False
    assert client.get("/api/v1/incidents").status_code == 401
    assert client.get("/api/v1/incidents").json()["detail"] == "Authentication required"


def test_invalid_session_cookie_is_rejected():
    _logout()
    client.cookies.set(settings.session_cookie_name, "not-a-real-session-token")
    try:
        session = client.get("/api/v1/auth/session")
        assert session.status_code == 200
        assert session.json()["authenticated"] is False
        denied = client.get("/api/v1/incidents")
        assert denied.status_code == 401
        assert denied.json()["detail"] == "Authentication required"
    finally:
        client.cookies.delete(settings.session_cookie_name)


def test_expired_session_is_rejected_and_removed():
    store = SessionStore(backend=MemorySessionBackend())
    sid = "sid-expired-rc1"
    store.save(
        sid,
        {
            "operator": "operator",
            "role": "Operator",
            "organization_id": "org-aviation-east",
            "site_id": "site-cyul",
            "created_at": _utcnow() - timedelta(hours=2),
            "expires_at": _utcnow() - timedelta(seconds=5),
            "auth_method": "session",
        },
    )
    assert store.get(sid) is None
    assert store.count() == 0


def test_session_save_does_not_resurrect_expired_record():
    store = SessionStore(backend=MemorySessionBackend())
    sid = "sid-ttl-rc1"
    store.save(
        sid,
        {
            "operator": "operator",
            "role": "Operator",
            "organization_id": "org-aviation-east",
            "site_id": "site-cyul",
            "created_at": _utcnow(),
            "expires_at": _utcnow() - timedelta(seconds=1),
        },
    )
    assert store.get(sid) is None


def test_bearer_jwt_is_not_accepted_as_operator_session():
    """Architecture is opaque cookies. A JWT-shaped Bearer token is not a session."""
    _logout()
    fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJBZG1pbmlzdHJhdG9yIn0.sig"
    denied = client.get("/api/v1/incidents", headers={"Authorization": f"Bearer {fake_jwt}"})
    assert denied.status_code == 401
    assert denied.json()["detail"] == "Authentication required"


def test_refresh_token_endpoint_is_not_implemented():
    _logout()
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "anything"})
    assert response.status_code == 404


def test_login_and_logout_are_audited():
    _logout()
    _login("admin")
    events = client.get("/admin/audit", params={"action": "auth.login", "limit": 50})
    assert events.status_code == 200
    assert any(item["action"] == "auth.login" and item["actor"] == "admin" for item in events.json())

    client.post("/api/v1/auth/logout")
    _login("admin")
    logout_events = client.get("/admin/audit", params={"action": "auth.logout", "limit": 50})
    assert logout_events.status_code == 200
    assert any(item["action"] == "auth.logout" and item["actor"] == "admin" for item in logout_events.json())


def test_failed_login_writes_security_login_failure():
    _logout()
    denied = client.post("/api/v1/auth/login", json={"operator": "admin", "password": "wrong-password"})
    assert denied.status_code == 401
    _login("admin")
    events = client.get("/admin/audit", params={"action": "security.login_failure", "limit": 50})
    assert events.status_code == 200
    assert any(item["action"] == "security.login_failure" for item in events.json())


def test_rate_limited_login_is_audited():
    rate_limiter.reset()
    previous = settings.rate_limit_login_per_minute
    object.__setattr__(settings, "rate_limit_login_per_minute", 1)
    try:
        first = client.post("/api/v1/auth/login", json={"operator": "admin", "password": "wrong-password"})
        assert first.status_code in {401, 429}
        limited = client.post("/api/v1/auth/login", json={"operator": "admin", "password": "wrong-password"})
        assert limited.status_code == 429
        assert limited.json()["detail"] == "Rate limit exceeded"
    finally:
        object.__setattr__(settings, "rate_limit_login_per_minute", previous)
        rate_limiter.reset()

    _login("admin")
    events = client.get("/admin/audit", params={"action": "security.login_failure", "limit": 80})
    assert events.status_code == 200
    assert any(
        item["action"] == "security.login_failure" and "rate_limited" in str(item.get("details") or "")
        for item in events.json()
    )


def test_rbac_viewer_forbidden_operator_allowed():
    _logout()
    _login("viewer")
    denied = client.post(
        "/api/v1/incidents",
        json={"title": "RC1 viewer denied", "severity": "low", "summary": "rbac"},
    )
    assert denied.status_code == 403
    _logout()
    _login("operator")
    allowed = client.post(
        "/api/v1/incidents",
        json={"title": "RC1 operator allowed", "severity": "low", "summary": "rbac"},
    )
    assert allowed.status_code == 201


def test_tenant_context_is_stamped_on_session():
    _logout()
    _login("operator")
    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200
    body = session.json()
    assert body["authenticated"] is True
    assert body["organization_id"]
    assert body["site_id"]
    context = client.get("/api/v1/auth/context")
    assert context.status_code == 200
    payload = context.json()
    assert payload["organization"]["organization_id"] == body["organization_id"]
    assert payload["site"]["site_id"] == body["site_id"]


def test_tenant_switch_denied_for_east_only_operator():
    _logout()
    _login("operator")
    denied = client.post(
        "/api/v1/auth/context",
        json={"organization_id": "org-aviation-west", "site_id": "site-cyvr"},
    )
    assert denied.status_code == 403


def test_protected_endpoints_require_authentication():
    _logout()
    paths = [
        "/api/v1/incidents",
        "/api/v1/dashboard/summary",
        "/api/v1/alerts",
        "/api/v1/platform/status",
        "/api/v1/auth/context",
        "/api/v1/fleet/aircraft",
        "/admin/system",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 401, f"{path} expected 401 got {response.status_code}"


def test_probes_remain_public():
    _logout()
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/live").status_code == 200
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/ready").status_code == 200


def test_openapi_documents_auth_and_session_cookie():
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    body = spec.json()
    tags = {t["name"]: t for t in body.get("tags") or []}
    assert "auth" in tags
    assert "cookie" in (tags["auth"].get("description") or "").lower() or "session" in (
        tags["auth"].get("description") or ""
    ).lower()
    paths = body.get("paths") or {}
    for path in (
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/session",
        "/api/v1/auth/context",
    ):
        assert path in paths, path
    schemes = (body.get("components") or {}).get("securitySchemes") or {}
    assert "SessionCookie" in schemes
    cookie = schemes["SessionCookie"]
    assert cookie["type"] == "apiKey"
    assert cookie["in"] == "cookie"
    assert cookie["name"] == settings.session_cookie_name
    description = (cookie.get("description") or "").lower()
    assert "jwt" in description
    incidents = paths.get("/api/v1/incidents") or {}
    get_op = incidents.get("get") or {}
    assert {"SessionCookie": []} in (get_op.get("security") or [])
    login_op = (paths.get("/api/v1/auth/login") or {}).get("post") or {}
    assert not login_op.get("security")


def test_websocket_rejects_unauthenticated():
    _logout()
    try:
        with client.websocket_connect("/api/v1/ws"):
            raise AssertionError("unauthenticated websocket must not connect")
    except Exception as exc:
        name = type(exc).__name__
        text = str(exc)
        assert (
            name in {"WebSocketDisconnect", "WebSocketDenialResponse", "HTTPException"}
            or "1008" in text
            or "403" in text
            or "denied" in text.lower()
            or "accept" in text.lower()
        )


def test_frontend_auth_flow_uses_cookies_and_reprompts_on_401():
    api_js = (PACKAGE_ROOT / "frontend" / "js" / "api.js").read_text(encoding="utf-8")
    app_js = (PACKAGE_ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    index_html = (PACKAGE_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'credentials: "include"' in api_js
    assert "/auth/login" in api_js
    assert "/auth/logout" in api_js
    assert "/auth/session" in api_js
    assert "notifyAuthRequired" in api_js
    assert "mercury:auth-required" in api_js
    assert "ensureSession" in app_js
    assert "promptInteractiveLogin" in app_js
    assert "recoverExpiredSession" in app_js
    assert "loginOverlay" in index_html
    assert 'type="password"' in index_html


def test_process_session_store_still_validates_live_login():
    _logout()
    _login("operator")
    cookie = client.cookies.get(settings.session_cookie_name)
    assert cookie
    record = session_store.get(cookie)
    assert record is not None
    assert record["operator"] == "operator"
    _logout()
    assert session_store.get(cookie) is None
