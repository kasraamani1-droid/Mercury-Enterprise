"""Cycle 8 — internet-pilot activation pack (repo-side, no live IdP/DNS/certs)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import fakeredis
from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.core.config import Settings, expected_oidc_redirect_uri, settings
from app.main import app
from app.security.rate_limit import (
    CompositeRateLimiter,
    RateLimitStoreUnavailable,
    RedisFixedWindowRateLimiter,
    SlidingWindowRateLimiter,
    rate_limiter,
)
from app.security.redact import redact_text

client = TestClient(app)
PACKAGE_ROOT = Path(__file__).resolve().parents[2]

EXAMPLE_DOMAIN = "mercury.example.com"
EXAMPLE_ISSUER = "https://idp.example.test/realms/mercury"
EXAMPLE_JWKS = "https://idp.example.test/realms/mercury/protocol/openid-connect/certs"


def _logout():
    client.post("/api/v1/auth/logout")


def _login_admin():
    _logout()
    response = client.post(
        "/api/v1/auth/login",
        json={"operator": "admin", "password": TEST_AUTH_PASSWORD},
    )
    assert response.status_code == 200, response.text


def _production_probe(**overrides) -> Settings:
    probe = Settings.__new__(Settings)
    defaults = {
        "environment": "production",
        "auth_password": "production-grade-password",
        "session_cookie_secure": True,
        "https_enabled": True,
        "jwt_secret": "j" * 32,
        "cookie_secret": "c" * 32,
        "domain": EXAMPLE_DOMAIN,
        "letsencrypt_email": "ops@example.com",
        "require_oidc": True,
        "auth_mode": "oidc",
        "oidc_is_configured": True,
        "oidc_issuer": EXAMPLE_ISSUER,
        "oidc_client_id": "mercury-confidential",
        "oidc_redirect_uri": expected_oidc_redirect_uri(EXAMPLE_DOMAIN),
        "oidc_jwks_uri": EXAMPLE_JWKS,
        "oidc_discovery_url": "",
        "seed_demo_data": False,
        "cors_origins": [f"https://{EXAMPLE_DOMAIN}"],
        "redis_required": False,
        "redis_url": "",
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        object.__setattr__(probe, key, value)
    return probe


def test_expected_oidc_redirect_strips_scheme_from_domain():
    assert expected_oidc_redirect_uri("https://ops.example.test/") == (
        "https://ops.example.test/api/v1/auth/oidc/callback"
    )


def test_https_oidc_requires_redirect_matching_domain():
    probe = _production_probe(oidc_redirect_uri="https://wrong.example.test/api/v1/auth/oidc/callback")
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected redirect mismatch")
    except RuntimeError as exc:
        assert "REDIRECT_URI" in str(exc)


def test_https_oidc_rejects_http_issuer_and_loopback():
    probe = _production_probe(oidc_issuer="http://idp.example.test/realms/mercury")
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected http issuer rejection")
    except RuntimeError as exc:
        assert "MERCURY_OIDC_ISSUER" in str(exc)

    probe = _production_probe(oidc_issuer="https://localhost/realms/mercury")
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected loopback issuer rejection")
    except RuntimeError as exc:
        assert "MERCURY_OIDC_ISSUER" in str(exc)


def test_https_oidc_requires_jwks_uri():
    probe = _production_probe(oidc_jwks_uri="")
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected missing JWKS URI")
    except RuntimeError as exc:
        assert "MERCURY_OIDC_JWKS_URI" in str(exc)


def test_https_oidc_rejects_issuer_equal_to_domain():
    probe = _production_probe(oidc_issuer=f"https://{EXAMPLE_DOMAIN}")
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected issuer==domain rejection")
    except RuntimeError as exc:
        assert "ISSUER" in str(exc)


def test_https_cors_must_include_domain_origin():
    probe = _production_probe(
        oidc_is_configured=False,
        require_oidc=False,
        auth_mode="password",
        https_enabled=True,
        cors_origins=["https://unrelated.example.test"],
    )
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected CORS domain origin requirement")
    except RuntimeError as exc:
        assert "CORS" in str(exc) or "DOMAIN" in str(exc)


def test_redis_rate_limiter_is_shared_across_workers():
    fake = fakeredis.FakeRedis(decode_responses=True)
    worker_a = CompositeRateLimiter()
    worker_b = CompositeRateLimiter()
    worker_a.attach_redis(fake)
    worker_b.attach_redis(fake)
    assert worker_a.allow("login:203.0.113.10", 3, 60.0) is True
    assert worker_b.allow("login:203.0.113.10", 3, 60.0) is True
    assert worker_a.allow("login:203.0.113.10", 3, 60.0) is True
    assert worker_b.allow("login:203.0.113.10", 3, 60.0) is False
    worker_a.reset()
    assert worker_b.allow("login:203.0.113.10", 3, 60.0) is True


def test_in_process_rate_limiter_is_not_shared():
    a = SlidingWindowRateLimiter()
    b = SlidingWindowRateLimiter()
    assert a.allow("login:10.0.0.1", 1, 60.0) is True
    assert b.allow("login:10.0.0.1", 1, 60.0) is True
    assert a.allow("login:10.0.0.1", 1, 60.0) is False


def test_redis_required_rate_limit_fails_closed():
    class DeadRedis:
        def incr(self, *_a, **_k):
            raise ConnectionError("down")

        def expire(self, *_a, **_k):
            return True

        def ttl(self, *_a, **_k):
            return 10

        def scan_iter(self, **_k):
            return iter(())

        def delete(self, *_a, **_k):
            return 0

    limiter = RedisFixedWindowRateLimiter(DeadRedis())
    try:
        limiter.allow("api:10.1.1.1", 10, 60.0)
        raise AssertionError("expected RateLimitStoreUnavailable")
    except RateLimitStoreUnavailable:
        pass


def test_global_rate_limiter_uses_fakeredis_when_attached():
    fake = fakeredis.FakeRedis(decode_responses=True)
    previous_required = settings.redis_required
    object.__setattr__(settings, "redis_required", True)
    object.__setattr__(settings, "rate_limit_login_per_minute", 2)
    rate_limiter.reset()
    rate_limiter.attach_redis(fake)
    try:
        codes = []
        for _ in range(4):
            response = client.post(
                "/api/v1/auth/login",
                json={"operator": "operator", "password": "wrong-password"},
            )
            codes.append(response.status_code)
        assert 429 in codes
        assert rate_limiter.backend_name == "redis"
    finally:
        rate_limiter.detach_redis()
        object.__setattr__(settings, "redis_required", previous_required)
        object.__setattr__(settings, "rate_limit_login_per_minute", 0)
        rate_limiter.reset()


def test_named_org_user_oidc_bind_round_trip():
    _login_admin()
    suffix = uuid.uuid4().hex[:8]
    username = f"pilot{suffix}"
    created = client.post(
        "/api/v1/org/users",
        json={
            "username": username,
            "password": "named-operator-password",
            "display_name": "Pilot Operator",
            "email": f"{username}@example.test",
            "oidc_issuer": EXAMPLE_ISSUER,
            "oidc_subject": f"sub-{suffix}",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["oidc_bound"] is True
    assert body["oidc_issuer"] == EXAMPLE_ISSUER
    assert body["oidc_subject"] == f"sub-{suffix}"
    assert "password" not in body

    other = f"pilotb{suffix}"
    assert (
        client.post(
            "/api/v1/org/users",
            json={
                "username": other,
                "password": "named-operator-password",
                "display_name": "Second",
            },
        ).status_code
        == 201
    )
    bound = client.post(
        f"/api/v1/org/users/{other}/oidc",
        json={"oidc_issuer": EXAMPLE_ISSUER, "oidc_subject": f"sub-b-{suffix}"},
    )
    assert bound.status_code == 200, bound.text
    assert bound.json()["oidc_bound"] is True

    conflict = client.post(
        f"/api/v1/org/users/{other}/oidc",
        json={"oidc_issuer": EXAMPLE_ISSUER, "oidc_subject": f"sub-{suffix}"},
    )
    assert conflict.status_code == 409
    _logout()


def test_oidc_bind_rejects_http_issuer():
    _login_admin()
    suffix = uuid.uuid4().hex[:8]
    username = f"badidp{suffix}"
    assert (
        client.post(
            "/api/v1/org/users",
            json={"username": username, "password": "named-operator-password"},
        ).status_code
        == 201
    )
    denied = client.post(
        f"/api/v1/org/users/{username}/oidc",
        json={"oidc_issuer": "http://idp.example.test", "oidc_subject": "abc"},
    )
    assert denied.status_code == 400
    _logout()


def test_health_and_ready_do_not_leak_secrets():
    health = client.get("/health")
    assert health.status_code == 200
    blob = health.text.lower()
    for needle in ("jwt_secret", "cookie_secret", "client_secret", "password=", TEST_AUTH_PASSWORD.lower()):
        assert needle not in blob
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert "redis://" not in ready.text.lower()


def test_audit_details_are_redacted():
    assert "password=***" in redact_text("password=super-secret-value")
    assert "client_secret=***" in redact_text("client_secret=abc")


def test_activation_docs_and_verify_script_exist():
    activation = (PACKAGE_ROOT / "docs" / "pilot" / "ACTIVATION.md").read_text(encoding="utf-8")
    assert "OWNER ACTION REQUIRED" in activation
    assert "Cursor can implement" in activation or "**A.**" in activation
    assert "Do NOT simulate" in activation or "does not exist" in activation.lower() or "not activated" in activation.lower()
    assert (PACKAGE_ROOT / "docs" / "pilot" / "OPERATORS.md").is_file()
    assert (PACKAGE_ROOT / "docs" / "pilot" / "ROLLBACK.md").is_file()
    assert (PACKAGE_ROOT / "scripts" / "verify_activation.py").is_file()
    overlay = (PACKAGE_ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    assert "noeviction" in overlay
    assert "ports: !reset []" in overlay
    env_example = (PACKAGE_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "MERCURY_OIDC_JWKS_URI=" in env_example
    assert re.search(r"^MERCURY_OIDC_JWKS_URI=\s*$", env_example, re.M)
    assert re.search(r"^POSTGRES_PASSWORD=\s*$", env_example, re.M)


def test_verify_activation_script_passes_without_printing_secrets():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(PACKAGE_ROOT / "scripts" / "verify_activation.py"), "--skip-docker"],
        cwd=str(PACKAGE_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    blob = (result.stdout + result.stderr).lower()
    assert "activation verify passed" in blob
    assert TEST_AUTH_PASSWORD.lower() not in blob


def test_no_invented_production_domain_in_compose_overlay():
    overlay = (PACKAGE_ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    assert "kasra" not in overlay.lower()
    assert "amazonaws.com" not in overlay
    assert "okta.com" not in overlay
    nginx_template = (PACKAGE_ROOT / "deploy" / "nginx-production.conf.template").read_text(encoding="utf-8")
    assert "${DOMAIN}" in nginx_template
    assert "X-Forwarded-Proto" in nginx_template
    assert "X-Forwarded-For" in nginx_template
