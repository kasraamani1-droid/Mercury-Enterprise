"""EPIC-001 platform hardening: pagination, Redis ready, dual-write, files, OpenAPI."""

from __future__ import annotations

from pathlib import Path

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.core.health import build_ready_payload, check_redis
from app.database import SessionLocal
from app.event_fabric.catalog import BUS_TO_CATALOG
from app.event_fabric.models import EnterpriseEventStore
from app.main import app
from app.platform.event_framework import event_framework
from app.platform.file_storage import local_disk_store, storage_root
from app.shared import MAX_PAGE, clamp_page
from sqlalchemy import select

client = TestClient(app)


def _logout():
    client.post("/api/v1/auth/logout")


def _login(operator: str = "admin"):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200, response.text
    return response


def test_clamp_page_hard_cap():
    lim, off = clamp_page(9999, -5)
    assert lim == MAX_PAGE
    assert off == 0


def test_fleet_aircraft_list_respects_limit_cap():
    _logout()
    _login("admin")
    rejected = client.get("/api/v1/fleet/aircraft", params={"limit": 9999})
    assert rejected.status_code == 422
    response = client.get("/api/v1/fleet/aircraft", params={"limit": 500})
    assert response.status_code == 200
    assert len(response.json()) <= MAX_PAGE


def test_org_organizations_list_accepts_pagination():
    _logout()
    _login("admin")
    response = client.get("/api/v1/organizations", params={"limit": 1, "offset": 0})
    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_personnel_employees_list_accepts_pagination():
    _logout()
    _login("admin")
    response = client.get("/api/v1/personnel/employees", params={"limit": 2, "offset": 0})
    assert response.status_code == 200
    assert len(response.json()) <= 2


def test_publications_list_accepts_pagination():
    _logout()
    _login("admin")
    response = client.get("/api/v1/publications", params={"limit": 2, "offset": 0})
    assert response.status_code == 200
    assert len(response.json()) <= 2


def test_approvals_list_respects_limit():
    _logout()
    _login("admin")
    response = client.get("/api/v1/approvals", params={"limit": 1})
    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_ready_fails_when_redis_required_and_missing(monkeypatch):
    object.__setattr__(settings, "redis_required", True)
    object.__setattr__(settings, "redis_url", "")
    try:
        db = SessionLocal()
        try:
            build_ready_payload(db)
            raise AssertionError("expected 503 when Redis required but not configured")
        except Exception as exc:
            from fastapi import HTTPException

            assert isinstance(exc, HTTPException)
            assert exc.status_code == 503
        finally:
            db.close()
    finally:
        object.__setattr__(settings, "redis_required", False)


def test_startup_validation_requires_redis_url_when_required():
    class _Probe:
        environment = "development"
        https_enabled = False
        session_cookie_secure = False
        auth_password = "production-grade-password-99"
        jwt_secret = ""
        cookie_secret = ""
        domain = ""
        letsencrypt_email = ""
        redis_required = True
        redis_url = ""

        def validate_for_startup(self):
            Settings.validate_for_startup(self)  # type: ignore[arg-type]

    try:
        _Probe().validate_for_startup()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "REDIS" in str(exc).upper()


def test_health_and_live_and_metrics():
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert "status" in body
    assert "redis" in body
    assert client.get("/live").status_code == 200
    metrics = client.get("/metrics")
    assert metrics.status_code == 200


def test_openapi_includes_platform_and_event_fabric():
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    paths = spec.json().get("paths", {})
    assert any(p.startswith("/api/v1/platform") for p in paths)
    assert any(p.startswith("/api/v1/event-fabric") or "event" in p for p in paths)
    assert "/api/v1/platform/files/upload" in paths


def test_dual_write_twin_created_maps_to_catalog():
    assert "twin.created" in BUS_TO_CATALOG
    org_id = "org-aviation-east"
    before = event_framework.recent(limit=5)
    event_framework.publish_sync(
        "twin.created",
        {"id": "twin-epic001-test", "twin_uuid": "tu-epic001", "actor": "admin"},
        organization_id=org_id,
        source="twin",
        actor="admin",
    )
    db = SessionLocal()
    try:
        row = db.scalar(
            select(EnterpriseEventStore)
            .where(
                EnterpriseEventStore.organization_id == org_id,
                EnterpriseEventStore.event_code == "TwinCreated",
            )
            .order_by(EnterpriseEventStore.occurred_at.desc())
        )
        assert row is not None
        assert row.bus_event_type in ("twin.created", "") or "twin" in (row.payload_json or "").lower() or row.event_code == "TwinCreated"
    finally:
        db.close()
    assert len(event_framework.recent(limit=5)) >= len(before)


def test_local_disk_object_store_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("MERCURY_FILE_STORAGE_ROOT", str(tmp_path))
    object.__setattr__(settings, "file_storage_root", str(tmp_path))
    uri, digest, size = local_disk_store.put_bytes(
        organization_id="org-aviation-east",
        filename="note.txt",
        content=b"epic001-bytes",
        content_type="text/plain",
    )
    assert size == 13
    assert len(digest) == 64
    assert uri.startswith("file:")
    root = storage_root()
    assert root == Path(tmp_path).resolve()
    files = list(root.rglob("*.txt"))
    assert files
    assert files[0].read_bytes() == b"epic001-bytes"


def test_platform_file_upload_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("MERCURY_FILE_STORAGE_ROOT", str(tmp_path))
    object.__setattr__(settings, "file_storage_root", str(tmp_path))
    _logout()
    _login("admin")
    response = client.post(
        "/api/v1/platform/files/upload",
        files={"file": ("hello.txt", b"hello-platform", "text/plain")},
        data={"file_class": "other"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["filename"] == "hello.txt"
    assert body["size_bytes"] == 14
    assert body["storage_uri"].startswith("file:")
    assert body["sha256"]


def test_check_redis_not_configured():
    object.__setattr__(settings, "redis_url", "")
    assert check_redis()["redis"] == "not_configured"
