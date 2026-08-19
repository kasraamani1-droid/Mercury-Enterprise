"""Cycle 6 — production IAM, OIDC boundary, secrets, SIM separation, CSRF, redaction."""

from __future__ import annotations

from pathlib import Path

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app
from app.security.csrf import csrf_blocked, origin_is_allowed
from app.security.oidc import OidcService, generate_pkce, public_auth_config, reset_pending_for_tests
from app.security.redact import redact_text

client = TestClient(app)
PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _logout():
    client.post("/api/v1/auth/logout")


def test_public_config_is_unauthenticated_and_secret_free():
    _logout()
    response = client.get("/api/v1/auth/public-config")
    assert response.status_code == 200
    body = response.json()
    assert body["lan_port_3000_is_not_production"] is True
    assert "password" not in str(body).lower() or "password_login_enabled" in body
    assert "client_secret" not in str(body).lower()
    assert "oidc_enabled" in body
    assert "sim_workspaces_visible" in body
    blob = str(body)
    assert TEST_AUTH_PASSWORD not in blob


def test_oidc_login_fails_closed_when_unconfigured():
    _logout()
    response = client.get("/api/v1/auth/oidc/login", follow_redirects=False)
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_oidc_callback_rejects_invalid_state():
    reset_pending_for_tests()
    response = client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": "abc", "state": "nope"},
        follow_redirects=False,
    )
    assert response.status_code in {401, 503}


def test_https_requires_oidc_configuration():
    probe = Settings.__new__(Settings)
    object.__setattr__(probe, "environment", "production")
    object.__setattr__(probe, "auth_password", "production-grade-password")
    object.__setattr__(probe, "session_cookie_secure", True)
    object.__setattr__(probe, "https_enabled", True)
    object.__setattr__(probe, "jwt_secret", "j" * 32)
    object.__setattr__(probe, "cookie_secret", "c" * 32)
    object.__setattr__(probe, "domain", "mercury.example.com")
    object.__setattr__(probe, "letsencrypt_email", "ops@example.com")
    object.__setattr__(probe, "require_oidc", True)
    object.__setattr__(probe, "auth_mode", "oidc")
    object.__setattr__(probe, "oidc_is_configured", False)
    object.__setattr__(probe, "seed_demo_data", False)
    object.__setattr__(probe, "cors_origins", ["https://mercury.example.com"])
    object.__setattr__(probe, "redis_required", False)
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected RuntimeError for missing OIDC")
    except RuntimeError as exc:
        assert "OIDC" in str(exc)


def test_production_refuses_demo_seed():
    probe = Settings.__new__(Settings)
    object.__setattr__(probe, "environment", "production")
    object.__setattr__(probe, "auth_password", "production-grade-password")
    object.__setattr__(probe, "session_cookie_secure", True)
    object.__setattr__(probe, "https_enabled", False)
    object.__setattr__(probe, "jwt_secret", "j" * 32)
    object.__setattr__(probe, "cookie_secret", "c" * 32)
    object.__setattr__(probe, "domain", "")
    object.__setattr__(probe, "letsencrypt_email", "")
    object.__setattr__(probe, "require_oidc", False)
    object.__setattr__(probe, "auth_mode", "password")
    object.__setattr__(probe, "oidc_is_configured", False)
    object.__setattr__(probe, "seed_demo_data", True)
    object.__setattr__(probe, "cors_origins", ["http://localhost:3000"])
    object.__setattr__(probe, "redis_required", False)
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected RuntimeError for demo seed")
    except RuntimeError as exc:
        assert "SEED_DEMO" in str(exc)


def test_production_cors_rejects_wildcard():
    probe = Settings.__new__(Settings)
    object.__setattr__(probe, "environment", "production")
    object.__setattr__(probe, "auth_password", "production-grade-password")
    object.__setattr__(probe, "session_cookie_secure", True)
    object.__setattr__(probe, "https_enabled", False)
    object.__setattr__(probe, "jwt_secret", "j" * 32)
    object.__setattr__(probe, "cookie_secret", "c" * 32)
    object.__setattr__(probe, "domain", "")
    object.__setattr__(probe, "letsencrypt_email", "")
    object.__setattr__(probe, "require_oidc", False)
    object.__setattr__(probe, "auth_mode", "password")
    object.__setattr__(probe, "oidc_is_configured", False)
    object.__setattr__(probe, "seed_demo_data", False)
    object.__setattr__(probe, "cors_origins", ["*"])
    object.__setattr__(probe, "redis_required", False)
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected RuntimeError for wildcard CORS")
    except RuntimeError as exc:
        assert "wildcard" in str(exc).lower() or "CORS" in str(exc)


def test_https_cors_rejects_port_3000():
    probe = Settings.__new__(Settings)
    object.__setattr__(probe, "environment", "production")
    object.__setattr__(probe, "auth_password", "production-grade-password")
    object.__setattr__(probe, "session_cookie_secure", True)
    object.__setattr__(probe, "https_enabled", True)
    object.__setattr__(probe, "jwt_secret", "j" * 32)
    object.__setattr__(probe, "cookie_secret", "c" * 32)
    object.__setattr__(probe, "domain", "mercury.example.com")
    object.__setattr__(probe, "letsencrypt_email", "ops@example.com")
    object.__setattr__(probe, "require_oidc", False)
    object.__setattr__(probe, "auth_mode", "password")
    object.__setattr__(probe, "oidc_is_configured", False)
    object.__setattr__(probe, "seed_demo_data", False)
    object.__setattr__(probe, "cors_origins", ["http://localhost:3000"])
    object.__setattr__(probe, "redis_required", False)
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected RuntimeError for :3000 CORS on HTTPS")
    except RuntimeError as exc:
        assert "3000" in str(exc)


def test_password_login_disabled_when_auth_mode_oidc():
    from app.core import config as config_mod

    previous = config_mod.settings.password_login_enabled
    object.__setattr__(config_mod.settings, "password_login_enabled", False)
    try:
        _logout()
        response = client.post(
            "/api/v1/auth/login",
            json={"operator": "operator", "password": TEST_AUTH_PASSWORD},
        )
        assert response.status_code == 403
        assert "sso" in response.json()["detail"].lower() or "password" in response.json()["detail"].lower()
    finally:
        object.__setattr__(config_mod.settings, "password_login_enabled", previous)


def test_oidc_flow_maps_provisioned_user_and_sets_cookie():
    reset_pending_for_tests()
    from app.core import config as config_mod
    from app.security import oidc as oidc_mod

    monkey_settings = config_mod.settings
    object.__setattr__(monkey_settings, "oidc_is_configured", True)
    object.__setattr__(monkey_settings, "oidc_issuer", "https://idp.example.test")
    object.__setattr__(monkey_settings, "oidc_client_id", "mercury-client")
    object.__setattr__(monkey_settings, "oidc_client_secret", "not-a-production-secret-value")
    object.__setattr__(monkey_settings, "oidc_redirect_uri", "https://mercury.example.test/api/v1/auth/oidc/callback")
    object.__setattr__(monkey_settings, "oidc_auto_provision", False)

    discovery = {
        "issuer": "https://idp.example.test",
        "authorization_endpoint": "https://idp.example.test/authorize",
        "token_endpoint": "https://idp.example.test/token",
        "userinfo_endpoint": "https://idp.example.test/userinfo",
    }

    def http_get(url: str, headers=None):
        if "userinfo" in url:
            return {
                "sub": "oidc-operator-1",
                "preferred_username": "operator",
                "email": "operator@example.test",
                "name": "Operator",
            }
        return discovery

    def http_post_form(url: str, fields, headers=None):
        assert fields.get("code_verifier")
        assert "password" not in str(fields).lower() or fields.get("client_secret")
        return {"access_token": "opaque-access-token", "token_type": "Bearer"}

    service = OidcService(http_get=http_get, http_post_form=http_post_form)
    previous = oidc_mod.oidc_service
    oidc_mod.oidc_service = service
    from app import main as main_mod

    main_mod.oidc_service = service
    try:
        start = client.get("/api/v1/auth/oidc/login", follow_redirects=False)
        assert start.status_code == 302
        location = start.headers.get("location") or ""
        assert "code_challenge" in location
        assert "state=" in location
        from urllib.parse import parse_qs, urlparse

        state = parse_qs(urlparse(location).query).get("state", [""])[0]
        assert state
        callback = client.get(
            "/api/v1/auth/oidc/callback",
            params={"code": "auth-code", "state": state},
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )
        assert callback.status_code == 200, callback.text
        body = callback.json()
        assert body["authenticated"] is True
        assert body["operator"] == "operator"
        assert body["auth_method"] == "oidc"
        assert "access_token" not in body
        cookie = (callback.headers.get("set-cookie") or "").lower()
        assert "httponly" in cookie
        session = client.get("/api/v1/auth/session")
        assert session.json()["authenticated"] is True
    finally:
        oidc_mod.oidc_service = previous
        main_mod.oidc_service = previous
        object.__setattr__(monkey_settings, "oidc_is_configured", False)
        object.__setattr__(monkey_settings, "oidc_issuer", "")
        object.__setattr__(monkey_settings, "oidc_client_id", "")
        object.__setattr__(monkey_settings, "oidc_client_secret", "")
        object.__setattr__(monkey_settings, "oidc_redirect_uri", "")
        _logout()


def test_pkce_verifier_is_not_the_challenge():
    verifier, challenge = generate_pkce()
    assert verifier != challenge
    assert len(verifier) >= 32
    assert len(challenge) >= 32


def test_log_redaction_strips_secrets():
    raw = "password=super-secret-value Authorization=Bearer abc.def cookie=mercury_session=tok"
    redacted = redact_text(raw)
    assert "super-secret-value" not in redacted
    assert "abc.def" not in redacted
    assert "***" in redacted


def test_login_audit_does_not_store_session_cookie():
    _logout()
    login = client.post(
        "/api/v1/auth/login",
        json={"operator": "admin", "password": TEST_AUTH_PASSWORD},
    )
    assert login.status_code == 200
    cookie = client.cookies.get("mercury_session") or ""
    events = client.get("/admin/audit", params={"action": "auth.login", "limit": 20})
    assert events.status_code == 200
    blob = str(events.json())
    if cookie:
        assert cookie not in blob
    assert "method=password" in blob


def test_csrf_rejects_foreign_origin():
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/fleet/aircraft",
        "headers": [(b"origin", b"https://evil.example")],
        "query_string": b"",
    }
    request = Request(scope)
    assert csrf_blocked(request, cors_origins=["http://localhost:3000"], domain="mercury.example.com") is True
    assert origin_is_allowed("http://localhost:3000", cors_origins=["http://localhost:3000"]) is True


def test_csrf_middleware_blocks_foreign_origin_on_login():
    _logout()
    response = client.post(
        "/api/v1/auth/login",
        json={"operator": "operator", "password": TEST_AUTH_PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert "csrf" in response.json()["detail"].lower()


def test_unauthenticated_and_forged_session_are_rejected():
    _logout()
    assert client.get("/api/v1/fleet/aircraft").status_code == 401
    client.cookies.set(settings.session_cookie_name, "forged-session")
    assert client.get("/api/v1/fleet/aircraft").status_code == 401
    _logout()


def test_production_directory_omits_shared_demo_users():
    from app.core import config as config_mod
    from app.main import directory_roles

    previous = config_mod.settings.seed_demo_data
    object.__setattr__(config_mod.settings, "seed_demo_data", False)
    try:
        roles = directory_roles()
        assert "viewer" not in roles
        assert "reviewer" not in roles
        assert "admin" in roles
        assert config_mod.settings.auth_operator in roles
    finally:
        object.__setattr__(config_mod.settings, "seed_demo_data", previous)


def test_org_user_model_has_oidc_columns():
    from app.org.models import OrgUser

    columns = OrgUser.__table__.c
    assert "oidc_issuer" in columns
    assert "oidc_subject" in columns


def test_restore_script_refuses_without_confirm_and_cleans_decrypt_tmp():
    restore_sh = (PACKAGE_ROOT / "scripts" / "restore_database.sh").read_text(encoding="utf-8")
    assert 'MERCURY_RESTORE_CONFIRM' in restore_sh
    assert '!= "YES"' in restore_sh
    assert "cleanup_decrypt_tmp" in restore_sh


def test_frontend_hides_or_labels_sim_and_exposes_sso():
    html = (PACKAGE_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'id="oidcLoginLink"' in html
    registry = (PACKAGE_ROOT / "frontend" / "js" / "ux2" / "registry.js").read_text(encoding="utf-8")
    assert "setSimWorkspacesVisible" in registry
    assert "simulated: true" in registry
    app_js = (PACKAGE_ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert "getPublicAuthConfig" in app_js
    compose = (PACKAGE_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "not internet-facing" in compose.lower() or "trusted-network" in compose.lower()
    overlay = (PACKAGE_ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    assert "ports: !reset []" in overlay
    assert "${POSTGRES_PASSWORD:?" in overlay
    assert "setSimWorkspacesVisible(false)" in app_js
    env_example = (PACKAGE_ROOT / ".env.example").read_text(encoding="utf-8")
    for key in ("MERCURY_OIDC_ISSUER", "MERCURY_OIDC_CLIENT_ID", "MERCURY_OIDC_CLIENT_SECRET", "MERCURY_OIDC_REDIRECT_URI"):
        assert key in env_example
        assert f"{key}=" in env_example
    nginx = (PACKAGE_ROOT / "deploy" / "nginx-production.conf.template").read_text(encoding="utf-8")
    assert "auth/oidc/login" in nginx
    assert "auth/oidc/callback" in nginx


def test_public_auth_config_helper_matches_settings():
    payload = public_auth_config()
    assert payload["password_login_enabled"] is True
    assert payload["oidc_enabled"] is False
