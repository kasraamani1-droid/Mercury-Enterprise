"""Security verification for production hardening (Phase 4)."""

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app

client = TestClient(app)


def _logout():
    client.post("/api/v1/auth/logout")


def _login(operator: str = "operator"):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200


def test_anonymous_incident_gets_denied():
    _logout()
    assert client.get("/api/v1/incidents").status_code == 401
    assert client.get("/api/v1/incidents/does-not-exist").status_code == 401


def test_anonymous_ops_coordinate_denied():
    _logout()
    assert client.post("/api/v1/ops/coordinate", json={"event_type": "x", "payload": {}}).status_code == 401


def test_anonymous_sensitive_reads_denied():
    _logout()
    assert client.get("/api/v1/alerts").status_code == 401
    assert client.get("/api/v1/dashboard/summary").status_code == 401
    assert client.get("/api/v1/platform/status").status_code == 401
    assert client.get("/api/v1/ops/health").status_code == 401
    assert client.get("/api/v1/integrations").status_code == 401
    assert client.get("/api/v1/compliance").status_code == 401


def test_probes_remain_public():
    _logout()
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/ready").status_code == 200


def test_viewer_cannot_coordinate_ops():
    _login("viewer")
    assert client.post("/api/v1/ops/coordinate", json={"event_type": "x", "payload": {}}).status_code == 403


def test_viewer_can_read_incidents():
    _login("viewer")
    assert client.get("/api/v1/incidents").status_code == 200


def test_incident_list_respects_limit_cap():
    _login("operator")
    rejected = client.get("/api/v1/incidents", params={"limit": 9999})
    assert rejected.status_code == 422
    response = client.get("/api/v1/incidents", params={"limit": 500})
    assert response.status_code == 200
    assert len(response.json()) <= 500


def test_forbidden_demo_password_rejected_at_startup():
    class _Probe:
        environment = "development"
        auth_password = "mercury-demo"

        def validate_for_startup(self):
            Settings.validate_for_startup(self)  # type: ignore[arg-type]

    try:
        _Probe().validate_for_startup()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "forbidden" in str(exc).lower() or "MERCURY_AUTH_PASSWORD" in str(exc)


def test_missing_password_rejected_at_startup():
    class _Probe:
        environment = "development"
        auth_password = ""

        def validate_for_startup(self):
            Settings.validate_for_startup(self)  # type: ignore[arg-type]

    try:
        _Probe().validate_for_startup()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "MERCURY_AUTH_PASSWORD" in str(exc)
