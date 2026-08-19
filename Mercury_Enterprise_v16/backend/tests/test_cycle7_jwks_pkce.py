"""Cycle 7 — JWKS ID-token verification, Redis PKCE/state, session fail-closed."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import fakeredis
from conftest import TEST_AUTH_PASSWORD
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app
from app.security.jwks import JwksCache, verify_id_token
from app.security.oidc import OidcService, reset_pending_for_tests
from app.security.oidc_pending import MemoryPendingStore, RedisPendingStore, build_pending_store
from app.security.sessions import session_store
from oidc_test_idp import (
    AUDIENCE,
    EC_KID,
    ISSUER,
    KID,
    SUBJECT,
    default_claims,
    ec_jwk,
    generate_ec_pair,
    generate_rsa_pair,
    jwks_document,
    rsa_jwk,
    sign_id_token,
    unsigned_alg_none_token,
)

client = TestClient(app)
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
RSA_PRIVATE, RSA_PUBLIC = generate_rsa_pair()
RSA_ALT_PRIVATE, RSA_ALT_PUBLIC = generate_rsa_pair()
EC_PRIVATE, EC_PUBLIC = generate_ec_pair()
RSA_JWKS = jwks_document(rsa_jwk(RSA_PUBLIC))
EC_JWKS = jwks_document(ec_jwk(EC_PUBLIC))


def _logout():
    client.post("/api/v1/auth/logout")


def _configure_oidc_settings() -> None:
    object.__setattr__(settings, "oidc_is_configured", True)
    object.__setattr__(settings, "oidc_issuer", ISSUER)
    object.__setattr__(settings, "oidc_client_id", AUDIENCE)
    object.__setattr__(settings, "oidc_client_secret", "not-a-production-secret-value")
    object.__setattr__(settings, "oidc_redirect_uri", "https://mercury.example.test/api/v1/auth/oidc/callback")
    object.__setattr__(settings, "oidc_auto_provision", False)
    object.__setattr__(settings, "oidc_clock_skew_seconds", 60)
    object.__setattr__(settings, "oidc_jwks_cache_seconds", 300)


def _clear_oidc_settings() -> None:
    object.__setattr__(settings, "oidc_is_configured", False)
    object.__setattr__(settings, "oidc_issuer", "")
    object.__setattr__(settings, "oidc_client_id", "")
    object.__setattr__(settings, "oidc_client_secret", "")
    object.__setattr__(settings, "oidc_redirect_uri", "")
    object.__setattr__(settings, "oidc_pkce_require_redis", False)
    object.__setattr__(settings, "redis_url", "")
    _logout()


def test_jwks_valid_rs256_and_es256():
    rs_token = sign_id_token(RSA_PRIVATE, kid=KID, claims=default_claims())
    rs_claims = verify_id_token(rs_token, issuer=ISSUER, audience=AUDIENCE, jwks=RSA_JWKS, nonce="test-nonce")
    assert rs_claims["sub"] == SUBJECT
    ec_token = sign_id_token(EC_PRIVATE, kid=EC_KID, alg="ES256", claims=default_claims())
    ec_claims = verify_id_token(ec_token, issuer=ISSUER, audience=AUDIENCE, jwks=EC_JWKS, nonce="test-nonce")
    assert ec_claims["sub"] == SUBJECT


def test_jwks_rejects_wrong_signature():
    token = sign_id_token(RSA_ALT_PRIVATE, kid=KID, claims=default_claims())
    try:
        verify_id_token(token, issuer=ISSUER, audience=AUDIENCE, jwks=RSA_JWKS, nonce="test-nonce")
        raise AssertionError("expected signature rejection")
    except HTTPException as exc:
        assert exc.status_code == 401


def test_jwks_rejects_wrong_issuer_and_audience():
    token = sign_id_token(RSA_PRIVATE, kid=KID, claims=default_claims(iss="https://evil.example"))
    try:
        verify_id_token(token, issuer=ISSUER, audience=AUDIENCE, jwks=RSA_JWKS, nonce="test-nonce")
        raise AssertionError("expected issuer rejection")
    except HTTPException as exc:
        assert exc.status_code == 401
    token = sign_id_token(RSA_PRIVATE, kid=KID, claims=default_claims(aud="other-client"))
    try:
        verify_id_token(token, issuer=ISSUER, audience=AUDIENCE, jwks=RSA_JWKS, nonce="test-nonce")
        raise AssertionError("expected audience rejection")
    except HTTPException as exc:
        assert exc.status_code == 401


def test_jwks_rejects_expired_token():
    now = int(time.time())
    token = sign_id_token(
        RSA_PRIVATE,
        kid=KID,
        claims=default_claims(exp=now - 120, iat=now - 180, nbf=now - 180),
    )
    try:
        verify_id_token(token, issuer=ISSUER, audience=AUDIENCE, jwks=RSA_JWKS, nonce="test-nonce", leeway_seconds=60)
        raise AssertionError("expected expiry rejection")
    except HTTPException as exc:
        assert exc.status_code == 401


def test_jwks_rejects_missing_kid_and_alg_none():
    token = jwt_encode_without_kid()
    try:
        verify_id_token(token, issuer=ISSUER, audience=AUDIENCE, jwks=RSA_JWKS, nonce="test-nonce")
        raise AssertionError("expected missing kid rejection")
    except HTTPException as exc:
        assert exc.status_code == 401
    try:
        verify_id_token(
            unsigned_alg_none_token(),
            issuer=ISSUER,
            audience=AUDIENCE,
            jwks=RSA_JWKS,
            nonce="test-nonce",
        )
        raise AssertionError("expected alg=none rejection")
    except HTTPException as exc:
        assert exc.status_code == 401


def jwt_encode_without_kid() -> str:
    import jwt

    return jwt.encode(default_claims(), RSA_PRIVATE, algorithm="RS256", headers={"typ": "JWT"})


def test_jwks_rejects_unknown_kid_and_expired_jwk():
    token = sign_id_token(RSA_PRIVATE, kid="no-such-kid", claims=default_claims())
    try:
        verify_id_token(token, issuer=ISSUER, audience=AUDIENCE, jwks=RSA_JWKS, nonce="test-nonce")
        raise AssertionError("expected unknown kid rejection")
    except HTTPException as exc:
        assert exc.status_code == 401
    expired = rsa_jwk(RSA_PUBLIC)
    expired["exp"] = int(time.time()) - 10
    token = sign_id_token(RSA_PRIVATE, kid=KID, claims=default_claims())
    try:
        verify_id_token(token, issuer=ISSUER, audience=AUDIENCE, jwks=jwks_document(expired), nonce="test-nonce")
        raise AssertionError("expected expired JWK rejection")
    except HTTPException as exc:
        assert exc.status_code == 401


def test_jwks_cache_refreshes_on_kid_miss():
    calls = {"n": 0}

    def http_get(url: str, headers=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return jwks_document(rsa_jwk(RSA_ALT_PUBLIC, kid="old"))
        return RSA_JWKS

    cache = JwksCache(http_get, ttl_seconds=300)
    token = sign_id_token(RSA_PRIVATE, kid=KID, claims=default_claims())
    document = cache.jwks_for_token("https://idp.example.test/jwks", token)
    assert document["keys"][0]["kid"] == KID
    assert calls["n"] == 2


def test_jwks_unavailable_fails_closed():
    def http_get(url: str, headers=None):
        raise ConnectionError("jwks down")

    cache = JwksCache(http_get, ttl_seconds=30)
    try:
        cache.fetch("https://idp.example.test/jwks")
        raise AssertionError("expected JWKS unavailable")
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "JWKS" in exc.detail


def _mock_oidc_http(id_token: str, *, userinfo_sub: str = SUBJECT):
    discovery = {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/authorize",
        "token_endpoint": f"{ISSUER}/token",
        "userinfo_endpoint": f"{ISSUER}/userinfo",
        "jwks_uri": f"{ISSUER}/jwks",
    }

    def http_get(url: str, headers=None):
        if "userinfo" in url:
            return {
                "sub": userinfo_sub,
                "preferred_username": "operator",
                "email": "operator@example.test",
                "name": "Operator",
            }
        if "jwks" in url:
            return RSA_JWKS
        return discovery

    def http_post_form(url: str, fields, headers=None):
        assert fields.get("code_verifier")
        return {"access_token": "opaque-access-token", "token_type": "Bearer", "id_token": id_token}

    return http_get, http_post_form


def test_oidc_callback_verifies_id_token_and_sets_secure_session_cookie():
    reset_pending_for_tests()
    _configure_oidc_settings()
    from app.security import oidc as oidc_mod
    from app import main as main_mod

    placeholder = sign_id_token(RSA_PRIVATE, kid=KID)
    http_get, http_post_form = _mock_oidc_http(placeholder)
    service = OidcService(http_get=http_get, http_post_form=http_post_form, pending_store=MemoryPendingStore())
    previous = oidc_mod.oidc_service
    oidc_mod.oidc_service = service
    main_mod.oidc_service = service
    try:
        start = client.get("/api/v1/auth/oidc/login", follow_redirects=False)
        assert start.status_code == 302
        query = parse_qs(urlparse(start.headers.get("location") or "").query)
        state = query.get("state", [""])[0]
        nonce = query.get("nonce", [""])[0]
        id_token = sign_id_token(RSA_PRIVATE, kid=KID, claims=default_claims(nonce=nonce))
        service._http_post_form = _mock_oidc_http(id_token)[1]
        callback = client.get(
            "/api/v1/auth/oidc/callback",
            params={"code": "auth-code", "state": state},
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )
        assert callback.status_code == 200, callback.text
        body = callback.json()
        assert body["authenticated"] is True
        assert body["auth_method"] == "oidc"
        assert "access_token" not in body
        assert "refresh_token" not in body
        cookie = (callback.headers.get("set-cookie") or "").lower()
        assert "httponly" in cookie
        assert "samesite=lax" in cookie
        session = client.get("/api/v1/auth/session")
        assert session.json()["authenticated"] is True
        fleet = client.get("/api/v1/fleet/aircraft")
        assert fleet.status_code == 200
        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 200
        assert logout.json()["authenticated"] is False
        assert client.get("/api/v1/auth/session").json()["authenticated"] is False
        assert client.get("/api/v1/fleet/aircraft").status_code == 401
    finally:
        oidc_mod.oidc_service = previous
        main_mod.oidc_service = previous
        _clear_oidc_settings()


def test_oidc_rejects_replayed_state_and_bad_id_token():
    reset_pending_for_tests()
    _configure_oidc_settings()
    from app.security import oidc as oidc_mod
    from app import main as main_mod

    http_get, http_post_form = _mock_oidc_http(sign_id_token(RSA_PRIVATE, kid=KID))
    store = MemoryPendingStore()
    service = OidcService(http_get=http_get, http_post_form=http_post_form, pending_store=store)
    previous = oidc_mod.oidc_service
    oidc_mod.oidc_service = service
    main_mod.oidc_service = service
    try:
        start = client.get("/api/v1/auth/oidc/login", follow_redirects=False)
        query = parse_qs(urlparse(start.headers.get("location") or "").query)
        state = query.get("state", [""])[0]
        nonce = query.get("nonce", [""])[0]
        id_token = sign_id_token(RSA_PRIVATE, kid=KID, claims=default_claims(nonce=nonce))
        service._http_post_form = _mock_oidc_http(id_token)[1]
        first = client.get(
            "/api/v1/auth/oidc/callback",
            params={"code": "auth-code", "state": state},
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )
        assert first.status_code == 200, first.text
        replay = client.get(
            "/api/v1/auth/oidc/callback",
            params={"code": "auth-code", "state": state},
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )
        assert replay.status_code == 401
        start = client.get("/api/v1/auth/oidc/login", follow_redirects=False)
        query = parse_qs(urlparse(start.headers.get("location") or "").query)
        state = query.get("state", [""])[0]
        service._http_post_form = _mock_oidc_http(unsigned_alg_none_token())[1]
        denied = client.get(
            "/api/v1/auth/oidc/callback",
            params={"code": "auth-code", "state": state},
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )
        assert denied.status_code == 401
    finally:
        oidc_mod.oidc_service = previous
        main_mod.oidc_service = previous
        _clear_oidc_settings()


def test_redis_pkce_shared_across_two_workers_and_replay_rejected():
    server = fakeredis.FakeServer()
    worker_a = RedisPendingStore(fakeredis.FakeRedis(server=server, decode_responses=True))
    worker_b = RedisPendingStore(fakeredis.FakeRedis(server=server, decode_responses=True))
    worker_a.save("state-shared", {"code_verifier": "verifier-1", "nonce": "nonce-1"}, ttl_seconds=60)
    consumed = worker_b.consume("state-shared")
    assert consumed == {"code_verifier": "verifier-1", "nonce": "nonce-1"}
    assert worker_a.consume("state-shared") is None
    assert worker_b.consume("state-shared") is None


def test_production_oidc_fails_closed_when_redis_down():
    previous_url = settings.redis_url
    previous_require = settings.oidc_pkce_require_redis
    object.__setattr__(settings, "redis_url", "redis://127.0.0.1:1/0")
    object.__setattr__(settings, "oidc_pkce_require_redis", True)
    try:
        try:
            build_pending_store()
            raise AssertionError("expected fail closed without Redis")
        except HTTPException as exc:
            assert exc.status_code == 503
            assert "state store" in exc.detail.lower()
        dead = RedisPendingStore(
            type(
                "DeadRedis",
                (),
                {
                    "setex": lambda self, *a, **k: (_ for _ in ()).throw(ConnectionError("down")),
                    "getdel": lambda self, *a, **k: (_ for _ in ()).throw(ConnectionError("down")),
                    "scan_iter": lambda self, *a, **k: iter(()),
                },
            )()
        )
        try:
            dead.save("s", {"code_verifier": "v"})
            raise AssertionError("expected Redis save fail closed")
        except HTTPException as exc:
            assert exc.status_code == 503
    finally:
        object.__setattr__(settings, "redis_url", previous_url)
        object.__setattr__(settings, "oidc_pkce_require_redis", previous_require)


def test_production_oidc_startup_requires_redis_url():
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
    object.__setattr__(probe, "oidc_is_configured", True)
    object.__setattr__(probe, "seed_demo_data", False)
    object.__setattr__(probe, "cors_origins", ["https://mercury.example.com"])
    object.__setattr__(probe, "redis_required", False)
    object.__setattr__(probe, "redis_url", "")
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected RuntimeError for missing Redis")
    except RuntimeError as exc:
        assert "REDIS_URL" in str(exc)


def test_expired_session_and_forged_cookie_are_unauthorized():
    _logout()
    login = client.post("/api/v1/auth/login", json={"operator": "operator", "password": TEST_AUTH_PASSWORD})
    assert login.status_code == 200
    session_id = client.cookies.get(settings.session_cookie_name)
    assert session_id
    record = session_store.get(session_id)
    assert record is not None
    record["expires_at"] = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5)
    session_store.save(session_id, record)
    assert client.get("/api/v1/fleet/aircraft").status_code == 401
    _logout()
    client.cookies.set(settings.session_cookie_name, "forged-session")
    assert client.get("/api/v1/fleet/aircraft").status_code == 401
    _logout()


def test_no_operator_refresh_token_endpoint():
    _logout()
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code in {404, 405, 401}
    login = client.post("/api/v1/auth/login", json={"operator": "operator", "password": TEST_AUTH_PASSWORD})
    assert "refresh_token" not in login.json()
    _logout()


def test_production_overlay_requires_redis_and_unpublishes_port_3000():
    overlay = (PACKAGE_ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    assert "ports: !reset []" in overlay
    assert 'REDIS_REQUIRED: "true"' in overlay
    assert '"--workers", "2"' in overlay
    dockerfile = (PACKAGE_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert '"--workers", "1"' in dockerfile
    env_example = (PACKAGE_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "MERCURY_OIDC_JWKS_CACHE_SECONDS" in env_example
    nginx = (PACKAGE_ROOT / "deploy" / "nginx-production.conf.template").read_text(encoding="utf-8")
    assert "listen 443 ssl" in nginx
    assert "auth/oidc/login" in nginx
    assert "auth/oidc/callback" in nginx
