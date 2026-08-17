"""RC1 API documentation — OpenAPI completeness for Swagger UI / ReDoc."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.openapi_docs import OPENAPI_TAGS, PUBLIC_OPS

client = TestClient(app)


def _spec() -> dict:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    return body


def _operations(spec: dict) -> list[tuple[str, str, dict]]:
    ops: list[tuple[str, str, dict]] = []
    for path, methods in (spec.get("paths") or {}).items():
        for method, op in methods.items():
            if method.startswith("x-") or not isinstance(op, dict):
                continue
            ops.append((path, method, op))
    return ops


def test_docs_and_redoc_are_served():
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert b"swagger" in docs.content.lower() or b"Swagger" in docs.content
    redoc = client.get("/redoc")
    assert redoc.status_code == 200
    assert b"redoc" in redoc.content.lower() or b"ReDoc" in redoc.content


def test_openapi_tag_catalog_covers_used_tags():
    spec = _spec()
    catalog = {item["name"]: item for item in spec.get("tags") or []}
    expected = {item["name"] for item in OPENAPI_TAGS}
    assert expected <= set(catalog)
    for name, item in catalog.items():
        assert (item.get("description") or "").strip(), name
    used: set[str] = set()
    for _path, _method, op in _operations(spec):
        used.update(op.get("tags") or [])
    missing = used - set(catalog)
    assert not missing, f"tags used without catalog: {sorted(missing)}"
    assert "Connectors" not in used
    assert "org" not in used


def test_every_operation_has_summary_description_tag_and_errors():
    spec = _spec()
    ops = _operations(spec)
    assert len(ops) >= 400
    for path, method, op in ops:
        assert (op.get("summary") or "").strip(), f"{method} {path} missing summary"
        desc = (op.get("description") or "").strip()
        assert desc, f"{method} {path} missing description"
        assert "validat" in desc.lower() or "422" in desc, f"{method} {path} missing validation docs"
        assert op.get("tags"), f"{method} {path} missing tag"
        responses = op.get("responses") or {}
        assert "422" in responses, f"{method} {path} missing 422"
        if (path, method.lower()) in PUBLIC_OPS:
            assert not op.get("security"), f"{method} {path} should be public"
        else:
            assert op.get("security"), f"{method} {path} missing security"
            assert "401" in responses, f"{method} {path} missing 401"
            assert "Authentication" in desc or "session" in desc.lower(), f"{method} {path} missing auth docs"
            assert "403" in responses, f"{method} {path} missing 403"


def test_protected_operations_document_session_or_api_key():
    spec = _spec()
    schemes = (spec.get("components") or {}).get("securitySchemes") or {}
    assert "SessionCookie" in schemes
    assert schemes["SessionCookie"]["in"] == "cookie"
    assert "ApiKeyAuth" in schemes
    assert schemes["ApiKeyAuth"]["name"] == "X-API-Key"
    incidents = ((spec.get("paths") or {}).get("/api/v1/incidents") or {}).get("get") or {}
    security = incidents.get("security") or []
    assert {"SessionCookie": []} in security
    assert {"ApiKeyAuth": []} in security


def test_success_responses_have_a_schema_or_plain_text():
    spec = _spec()
    for path, method, op in _operations(spec):
        if method == "delete":
            continue
        responses = op.get("responses") or {}
        success = responses.get("200") or responses.get("201")
        assert success, f"{method} {path} missing 200/201"
        content = (success.get("content") or {}) if isinstance(success, dict) else {}
        has_schema = any(
            isinstance(item, dict) and isinstance(item.get("schema"), dict) and bool(item.get("schema"))
            for item in content.values()
        )
        assert has_schema, f"{method} {path} success response has no schema"


def test_login_documents_example_and_rate_limit():
    spec = _spec()
    login = ((spec.get("paths") or {}).get("/api/v1/auth/login") or {}).get("post") or {}
    assert login.get("tags") == ["auth"]
    responses = login.get("responses") or {}
    assert "429" in responses
    example = (
        ((login.get("requestBody") or {}).get("content") or {})
        .get("application/json", {})
        .get("example")
    )
    schema_examples = (
        ((login.get("requestBody") or {}).get("content") or {})
        .get("application/json", {})
        .get("schema", {})
        .get("examples")
    )
    assert example or schema_examples
