"""Production security & infrastructure tests (v0.9.1)."""

from __future__ import annotations

import re
from pathlib import Path

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.security.rate_limit import rate_limiter

client = TestClient(app)

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
NGINX_PRODUCTION = PACKAGE_ROOT / "deploy" / "nginx-production.conf"
NGINX_TEMPLATE = PACKAGE_ROOT / "deploy" / "nginx-production.conf.template"


def _set_cookie_header(response) -> str:
    # Starlette/TestClient may expose set-cookie via headers.get or headers.getlist
    raw = response.headers.get("set-cookie")
    if raw:
        return raw
    getlist = getattr(response.headers, "getlist", None)
    if callable(getlist):
        parts = getlist("set-cookie")
        if parts:
            return ", ".join(parts)
    return ""


def test_root_health_ready_live_structured_json():
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] in {"ok", "degraded"}
    assert "version" in body
    assert "checks" in body
    assert "password" not in str(body).lower()

    ready = client.get("/ready")
    assert ready.status_code == 200
    ready_body = ready.json()
    assert ready_body["ready"] is True
    assert ready_body["status"] == "ok"
    assert ready_body["checks"]["database"] == "ok"

    live = client.get("/live")
    assert live.status_code == 200
    live_body = live.json()
    assert live_body["live"] is True
    assert live_body["status"] == "ok"
    assert "version" in live_body


def test_legacy_api_probes_still_work():
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/ready").status_code == 200


def test_secure_cookie_flags_on_login():
    client.post("/api/v1/auth/logout")
    response = client.post(
        "/api/v1/auth/login",
        json={"operator": "operator", "password": TEST_AUTH_PASSWORD},
    )
    assert response.status_code == 200
    cookie = _set_cookie_header(response).lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    # Secure follows settings; development may omit Secure, production must set it.
    from app.core.config import settings

    if settings.session_cookie_secure or settings.https_enabled:
        assert "secure" in cookie


def test_production_refuses_insecure_cookies():
    probe = Settings.__new__(Settings)
    object.__setattr__(probe, "environment", "production")
    object.__setattr__(probe, "auth_password", "production-grade-password")
    object.__setattr__(probe, "session_cookie_secure", False)
    object.__setattr__(probe, "https_enabled", False)
    object.__setattr__(probe, "jwt_secret", "x" * 32)
    object.__setattr__(probe, "cookie_secret", "y" * 32)
    object.__setattr__(probe, "domain", "mercury.example.com")
    object.__setattr__(probe, "letsencrypt_email", "ops@example.com")
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected RuntimeError for insecure cookies")
    except RuntimeError as exc:
        assert "secure" in str(exc).lower()


def test_production_requires_jwt_and_cookie_secrets():
    probe = Settings.__new__(Settings)
    object.__setattr__(probe, "environment", "production")
    object.__setattr__(probe, "auth_password", "production-grade-password")
    object.__setattr__(probe, "session_cookie_secure", True)
    object.__setattr__(probe, "https_enabled", True)
    object.__setattr__(probe, "jwt_secret", "")
    object.__setattr__(probe, "cookie_secret", "y" * 32)
    object.__setattr__(probe, "domain", "mercury.example.com")
    object.__setattr__(probe, "letsencrypt_email", "ops@example.com")
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected RuntimeError for missing JWT_SECRET")
    except RuntimeError as exc:
        assert "JWT_SECRET" in str(exc)


def test_rate_limit_login_returns_429():
    rate_limiter.reset()
    from app.core.config import settings

    previous = settings.rate_limit_login_per_minute
    object.__setattr__(settings, "rate_limit_login_per_minute", 2)
    try:
        codes = []
        for _ in range(4):
            response = client.post(
                "/api/v1/auth/login",
                json={"operator": "operator", "password": "wrong-password"},
            )
            codes.append(response.status_code)
        assert 429 in codes
        assert codes.count(429) >= 1
        limited = client.post(
            "/api/v1/auth/login",
            json={"operator": "operator", "password": "wrong-password"},
        )
        assert limited.status_code == 429
        assert limited.json()["detail"] == "Rate limit exceeded"
    finally:
        object.__setattr__(settings, "rate_limit_login_per_minute", previous)
        rate_limiter.reset()


def test_rate_limit_api_returns_429():
    rate_limiter.reset()
    from app.core.config import settings

    previous = settings.rate_limit_api_per_minute
    object.__setattr__(settings, "rate_limit_api_per_minute", 3)
    try:
        codes = [client.get("/api/v1/auth/session").status_code for _ in range(6)]
        assert 429 in codes
    finally:
        object.__setattr__(settings, "rate_limit_api_per_minute", previous)
        rate_limiter.reset()


def test_probes_are_not_rate_limited():
    rate_limiter.reset()
    from app.core.config import settings

    previous = settings.rate_limit_api_per_minute
    object.__setattr__(settings, "rate_limit_api_per_minute", 1)
    try:
        for _ in range(5):
            assert client.get("/live").status_code == 200
            assert client.get("/ready").status_code == 200
            assert client.get("/health").status_code == 200
    finally:
        object.__setattr__(settings, "rate_limit_api_per_minute", previous)
        rate_limiter.reset()


def test_nginx_http_redirects_to_https():
    for path in (NGINX_PRODUCTION, NGINX_TEMPLATE):
        text = path.read_text(encoding="utf-8")
        assert "return 301 https://" in text
        assert "ssl_protocols TLSv1.2 TLSv1.3" in text
        assert "limit_req_status 429" in text
        assert "Strict-Transport-Security" in text
        assert "Content-Security-Policy" in text
        assert "Cross-Origin-Opener-Policy" in text
        assert "Cross-Origin-Resource-Policy" in text
        assert "Permissions-Policy" in text
        assert re.search(r"proxy_set_header\s+Upgrade", text)
        assert "gzip on" in text
        assert "proxy_request_buffering on" in text
        assert "client_max_body_size" in text


def test_env_example_documents_required_secrets():
    env_example = (PACKAGE_ROOT / ".env.example").read_text(encoding="utf-8")
    for key in ("JWT_SECRET", "COOKIE_SECRET", "DOMAIN", "HTTPS_ENABLED", "LETSENCRYPT_EMAIL"):
        assert key in env_example
    # No insecure filled-in secrets
    assert not re.search(r"^JWT_SECRET=\S+", env_example, re.M) or re.search(
        r"^JWT_SECRET=\s*$", env_example, re.M
    )
    assert re.search(r"^COOKIE_SECRET=\s*$", env_example, re.M)
