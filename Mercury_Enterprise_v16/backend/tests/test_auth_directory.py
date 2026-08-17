"""Production authentication: OrgUser directory, Argon2id, durable identity."""

from __future__ import annotations

import hashlib
import uuid

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import DEV_PEPPER_FALLBACK, Settings
from app.database import SessionLocal
from app.main import app, seed_organizations
from app.org.models import OrgUser
from app.security.operators import (
    hash_password,
    operator_store,
    password_needs_rehash,
    verify_password,
)

client = TestClient(app)


def _login(operator: str = "admin", password: str = TEST_AUTH_PASSWORD):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def test_seeded_password_hashes_are_argon2id():
    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == "operator"))
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert user.platform_role == "Operator"
        assert verify_password(TEST_AUTH_PASSWORD, user.password_hash)
        assert not password_needs_rehash(user.password_hash) or user.password_hash.startswith("$argon2")
    finally:
        db.close()


def test_login_uses_org_user_after_in_memory_directory_cleared():
    snapshot = operator_store.snapshot()
    try:
        operator_store._operators.clear()
        response = client.post(
            "/api/v1/auth/login",
            json={"operator": "operator", "password": TEST_AUTH_PASSWORD},
        )
        assert response.status_code == 200
        assert response.json()["authenticated"] is True
        assert operator_store.get("operator") is not None
    finally:
        operator_store.hydrate((name, data["role"]) for name, data in snapshot.items())
        seed_organizations()


def test_org_created_user_survives_directory_clear():
    suffix = uuid.uuid4().hex[:8]
    username = f"persist{suffix}"
    password = "enterprise-user-password"
    _login("admin")
    created = client.post(
        "/api/v1/org/users",
        json={"username": username, "password": password, "display_name": "Persist Probe"},
    )
    assert created.status_code == 201
    membership = client.post(
        "/api/v1/memberships",
        json={
            "username": username,
            "organization_id": "org-aviation-east",
            "role": "Operator",
            "site_id": "site-cyul",
        },
    )
    assert membership.status_code == 201

    snapshot = operator_store.snapshot()
    try:
        operator_store._operators.clear()
        login = client.post("/api/v1/auth/login", json={"operator": username, "password": password})
        assert login.status_code == 200
        assert login.json()["role"] == "Operator"
    finally:
        operator_store.hydrate((name, data["role"]) for name, data in snapshot.items())
        seed_organizations()


def test_admin_created_user_is_persisted_on_org_user():
    suffix = uuid.uuid4().hex[:8]
    username = f"admuser{suffix}"
    _login("admin")
    created = client.post(
        "/admin/users",
        json={"operator": username, "password": "Observer-Pass-12345", "role": "Reviewer"},
    )
    assert created.status_code == 200, created.text
    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == username))
        assert user is not None
        assert user.platform_role == "Reviewer"
        assert user.password_hash.startswith("$argon2id$")
    finally:
        db.close()

    changed = client.post(
        "/admin/users/password",
        json={"operator": username, "password": "Observer-Pass-67890"},
    )
    assert changed.status_code == 200
    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == username))
        assert user is not None
        assert verify_password("Observer-Pass-67890", user.password_hash)
        assert not verify_password("Observer-Pass-12345", user.password_hash)
    finally:
        db.close()


def test_legacy_sha256_password_is_verified_and_rehashed():
    suffix = uuid.uuid4().hex[:8]
    username = f"legacy{suffix}"
    password = "enterprise-user-password"
    _login("admin")
    assert client.post(
        "/api/v1/org/users",
        json={"username": username, "password": password, "display_name": "Legacy Hash"},
    ).status_code == 201
    assert (
        client.post(
            "/api/v1/memberships",
            json={
                "username": username,
                "organization_id": "org-aviation-east",
                "role": "Viewer",
                "site_id": "site-cyul",
            },
        ).status_code
        == 201
    )

    legacy = hashlib.sha256(DEV_PEPPER_FALLBACK.encode("utf-8") + b"\0" + password.encode("utf-8")).hexdigest()
    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == username))
        assert user is not None
        user.password_hash = legacy
        db.commit()
    finally:
        db.close()

    login = client.post("/api/v1/auth/login", json={"operator": username, "password": password})
    assert login.status_code == 200

    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == username))
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(password, user.password_hash)
        assert user.password_hash != legacy
    finally:
        db.close()


def test_hash_password_never_returns_sha256_hex():
    hashed = hash_password("enterprise-user-password")
    assert hashed.startswith("$argon2id$")
    assert len(hashed) != 64 or not all(c in "0123456789abcdef" for c in hashed)


def test_unknown_user_login_is_generic_401():
    response = client.post(
        "/api/v1/auth/login",
        json={"operator": "does-not-exist-user", "password": "enterprise-user-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_inactive_user_cannot_authenticate():
    suffix = uuid.uuid4().hex[:8]
    username = f"inact{suffix}"
    password = "enterprise-user-password"
    _login("admin")
    assert client.post(
        "/api/v1/org/users",
        json={"username": username, "password": password},
    ).status_code == 201
    assert (
        client.post(
            "/api/v1/memberships",
            json={
                "username": username,
                "organization_id": "org-aviation-east",
                "role": "Viewer",
                "site_id": "site-cyul",
            },
        ).status_code
        == 201
    )
    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == username))
        assert user is not None
        user.status = "disabled"
        db.commit()
    finally:
        db.close()
    denied = client.post("/api/v1/auth/login", json={"operator": username, "password": password})
    assert denied.status_code == 401


def test_production_refuses_dev_pepper_secret():
    probe = Settings.__new__(Settings)
    object.__setattr__(probe, "environment", "production")
    object.__setattr__(probe, "auth_password", "production-grade-password")
    object.__setattr__(probe, "session_cookie_secure", True)
    object.__setattr__(probe, "https_enabled", True)
    object.__setattr__(probe, "jwt_secret", "x" * 32)
    object.__setattr__(probe, "cookie_secret", DEV_PEPPER_FALLBACK)
    object.__setattr__(probe, "domain", "mercury.example.com")
    object.__setattr__(probe, "letsencrypt_email", "ops@example.com")
    try:
        Settings.validate_for_startup(probe)
        raise AssertionError("expected RuntimeError for development pepper")
    except RuntimeError as exc:
        assert "COOKIE_SECRET" in str(exc)
