"""Sprint v0.9.2 — enterprise observability & operations."""

from __future__ import annotations

import uuid
from pathlib import Path

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[2]


def _login(operator: str = "admin"):
    response = client.post(
        "/api/v1/auth/login",
        json={"operator": operator, "password": TEST_AUTH_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response


def test_health_includes_observability_fields():
    body = client.get("/health").json()
    assert body["status"] in {"ok", "degraded"}
    assert "database" in body
    assert body["redis"] in {"ok", "error", "not_configured"}
    assert "disk" in body
    assert "memory" in body
    assert body["api_version"] == settings.version
    assert body["build_version"]
    assert body["uptime_seconds"] >= 0
    assert "password" not in str(body).lower()


def test_ready_and_live_include_versions():
    ready = client.get("/ready").json()
    assert ready["ready"] is True
    assert ready["api_version"]
    assert ready["build_version"]
    live = client.get("/live").json()
    assert live["live"] is True
    assert live["uptime_seconds"] >= 0


def test_prometheus_metrics_exposed():
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text
    assert "mercury_http_requests_total" in text
    assert "mercury_login_attempts_total" in text


def test_correlation_and_request_ids_echoed():
    response = client.get("/live", headers={"X-Correlation-ID": "corr-test-1"})
    assert response.status_code == 200
    assert response.headers.get("x-correlation-id") == "corr-test-1"
    assert response.headers.get("x-request-id")


def test_failed_login_is_audited_and_counted():
    before = client.post("/api/v1/auth/login", json={"operator": "admin", "password": "wrong-password"})
    assert before.status_code == 401
    _login("admin")
    events = client.get("/admin/audit", params={"action": "security.login_failure", "limit": 50})
    assert events.status_code == 200
    assert any(item["action"] == "security.login_failure" for item in events.json())


def test_admin_endpoints_require_admin():
    client.post("/api/v1/auth/logout")
    assert client.get("/admin/system").status_code == 401
    _login("operator")
    assert client.get("/admin/system").status_code == 403
    assert client.get("/admin/health").status_code == 403
    assert client.get("/admin/metrics").status_code == 403
    assert client.get("/admin/audit").status_code == 403


def test_admin_dashboard_and_user_lifecycle_audits():
    _login("admin")
    system = client.get("/admin/system")
    assert system.status_code == 200
    assert system.json()["api_version"]
    assert client.get("/admin/health").status_code == 200
    assert client.get("/admin/metrics").status_code == 200

    username = f"observer1{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/admin/users",
        json={"operator": username, "password": "Observer-Pass-12345", "role": "Viewer"},
    )
    assert created.status_code == 200, created.text
    password = client.post(
        "/admin/users/password",
        json={"operator": username, "password": "Observer-Pass-67890"},
    )
    assert password.status_code == 200
    role = client.post(
        "/admin/users/role",
        json={"operator": username, "role": "Reviewer"},
    )
    assert role.status_code == 200
    config = client.post(
        "/admin/config",
        json={"key": "LOG_LEVEL", "value": "INFO", "reason": "ops-test"},
    )
    assert config.status_code == 200

    audit = client.get("/admin/audit", params={"limit": 200})
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()}
    assert "user.create" in actions
    assert "user.password_change" in actions
    assert "user.role_change" in actions
    assert "config.change" in actions


def test_api_access_audit_on_mutating_call():
    previous = settings.audit_api_access
    object.__setattr__(settings, "audit_api_access", True)
    try:
        _login("operator")
        response = client.post(
            "/api/v1/incidents",
            json={"title": "Obs audit incident", "severity": "high", "description": "audit trail"},
        )
        assert response.status_code in {200, 201}
        _login("admin")
        audit = client.get("/admin/audit", params={"action": "api.access", "limit": 100})
        assert audit.status_code == 200
        assert any(item["action"] == "api.access" for item in audit.json())
    finally:
        object.__setattr__(settings, "audit_api_access", previous)


def test_backup_scripts_exist():
    for name in ("backup_database.sh", "restore_database.sh", "verify_backup.sh"):
        path = ROOT / "scripts" / name
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "set -eu" in text


def test_observability_docs_exist():
    for name in ("OBSERVABILITY.md", "AUDIT_LOGGING.md", "BACKUP.md", "MONITORING.md"):
        assert (ROOT / "docs" / name).is_file()
