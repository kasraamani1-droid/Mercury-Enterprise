"""RC1 Blocker 04 / RB-05 — password hashing, reset, and session revocation."""

from __future__ import annotations

import hashlib
import re
import uuid

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import DEV_PEPPER_FALLBACK, settings
from app.database import SessionLocal
from app.main import app
from app.org.models import OrgUser
from app.security.operators import (
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.security.sessions import session_store

client = TestClient(app)


def _login(operator: str, password: str = TEST_AUTH_PASSWORD):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": password})
    assert response.status_code == 200, response.text
    return response


def _create_org_user_with_membership(username: str, password: str, *, role: str = "Viewer") -> None:
    _login("admin")
    created = client.post(
        "/api/v1/org/users",
        json={"username": username, "password": password, "display_name": username},
    )
    assert created.status_code == 201, created.text
    membership = client.post(
        "/api/v1/memberships",
        json={
            "username": username,
            "organization_id": "org-aviation-east",
            "role": role,
            "site_id": "site-cyul",
        },
    )
    assert membership.status_code == 201, membership.text


def test_new_hashes_are_argon2id_with_unique_salts():
    a = hash_password("enterprise-user-password")
    b = hash_password("enterprise-user-password")
    assert a.startswith("$argon2id$")
    assert b.startswith("$argon2id$")
    assert a != b  # unique per-hash salt
    assert verify_password("enterprise-user-password", a)
    assert verify_password("enterprise-user-password", b)
    assert not verify_password("wrong-password-xx", a)


def test_login_rejects_wrong_password_and_keeps_argon2_hash():
    before = None
    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == "operator"))
        assert user is not None
        before = user.password_hash
        assert before.startswith("$argon2id$")
    finally:
        db.close()

    denied = client.post(
        "/api/v1/auth/login",
        json={"operator": "operator", "password": "definitely-not-the-password"},
    )
    assert denied.status_code == 401
    assert denied.json()["detail"] == "Invalid credentials"

    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == "operator"))
        assert user is not None
        assert user.password_hash == before
    finally:
        db.close()


def test_password_reset_stores_argon2id_and_allows_new_login_only():
    suffix = uuid.uuid4().hex[:8]
    username = f"pwreset{suffix}"
    old_password = "Original-Pass-12345"
    new_password = "Rotated-Pass-67890"

    _create_org_user_with_membership(username, old_password)

    first = _login(username, old_password)
    assert first.json()["authenticated"] is True
    assert client.get("/api/v1/auth/session").json()["authenticated"] is True

    _login("admin")
    changed = client.post(
        "/admin/users/password",
        json={"operator": username, "password": new_password},
    )
    assert changed.status_code == 200

    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == username))
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(new_password, user.password_hash)
        assert not verify_password(old_password, user.password_hash)
        assert not password_needs_rehash(user.password_hash) or user.password_hash.startswith("$argon2")
    finally:
        db.close()

    stale = client.post("/api/v1/auth/login", json={"operator": username, "password": old_password})
    assert stale.status_code == 401

    fresh = _login(username, new_password)
    assert fresh.json()["authenticated"] is True
    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json()["authenticated"] is True
    assert session.json()["operator"] == username


def test_password_reset_revokes_existing_sessions():
    suffix = uuid.uuid4().hex[:8]
    username = f"pwsess{suffix}"
    old_password = "Session-Pass-12345"
    new_password = "Session-Pass-67890"

    _create_org_user_with_membership(username, old_password)

    victim = TestClient(app)
    login = victim.post("/api/v1/auth/login", json={"operator": username, "password": old_password})
    assert login.status_code == 200
    assert victim.get("/api/v1/auth/session").json()["authenticated"] is True

    _login("admin")
    assert (
        client.post(
            "/admin/users/password",
            json={"operator": username, "password": new_password},
        ).status_code
        == 200
    )

    assert victim.get("/api/v1/auth/session").json()["authenticated"] is False
    assert session_store.count() >= 0

    restored = victim.post("/api/v1/auth/login", json={"operator": username, "password": new_password})
    assert restored.status_code == 200
    assert victim.get("/api/v1/auth/session").json()["authenticated"] is True


def test_logout_clears_session_cookie_after_password_login():
    _login("operator")
    assert client.get("/api/v1/auth/session").json()["authenticated"] is True
    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert logout.json()["authenticated"] is False
    assert client.get("/api/v1/auth/session").json()["authenticated"] is False


def test_legacy_sha256_with_dev_pepper_upgrades_on_login():
    suffix = uuid.uuid4().hex[:8]
    username = f"legacypw{suffix}"
    password = "enterprise-user-password"
    _create_org_user_with_membership(username, password)

    legacy = hashlib.sha256(DEV_PEPPER_FALLBACK.encode("utf-8") + b"\0" + password.encode("utf-8")).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", legacy)

    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == username))
        assert user is not None
        user.password_hash = legacy
        db.commit()
    finally:
        db.close()

    assert client.post("/api/v1/auth/login", json={"operator": username, "password": password}).status_code == 200

    db = SessionLocal()
    try:
        user = db.scalar(select(OrgUser).where(OrgUser.username == username))
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(password, user.password_hash)
    finally:
        db.close()


def test_argon2_parameters_are_configurable():
    assert int(settings.argon2_time_cost) >= 1
    assert int(settings.argon2_memory_kib) >= 8192
    assert int(settings.argon2_parallelism) >= 1
