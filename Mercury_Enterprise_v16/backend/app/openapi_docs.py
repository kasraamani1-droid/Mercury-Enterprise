"""OpenAPI documentation enrichment for Swagger UI / ReDoc (RC1 API docs).

Does not change request handling, permissions, or response filtering. It only
fills generated specification fields: tags, descriptions, security, and
documented error responses.
"""

from __future__ import annotations

from typing import Any

from fastapi.routing import APIRoute

from .core.config import settings

OPENAPI_TAGS: list[dict[str, str]] = [
    {"name": "probes", "description": "Liveness, readiness, health, and Prometheus metrics. Public except where metrics are disabled."},
    {"name": "auth", "description": "Operator login (password and OIDC/SSO), logout, session probe, public auth config, and tenant context. Cookie sessions; JWT is not a session mechanism."},
    {"name": "approvals", "description": "Durable tenant-scoped approval requests (request, list, approve, consume on incident resolve)."},
    {"name": "incidents", "description": "Command incidents, timeline events, evidence, assessment, and reports. Org/site scoped."},
    {"name": "audit", "description": "Operator audit trail (site-scoped). Administrators use /admin/audit for cross-site listing."},
    {"name": "reports", "description": "Incident/audit summary and history for the active site."},
    {"name": "alerts", "description": "In-memory operational alerts filtered to the active tenant."},
    {"name": "dashboard", "description": "Operator dashboard summary (mix of live domain counts and advisory/SIM fields)."},
    {"name": "decisions", "description": "Advisory decision engine evaluate/list/review. Not an operational authority."},
    {"name": "admin", "description": "Platform administrator surfaces — users, password, role, config, system health."},
    {"name": "connectors", "description": "External connector registry, health, and observations (feeds may be simulated)."},
    {"name": "ops", "description": "Operations coordination and health (advisory / simulated where noted)."},
    {"name": "organizations", "description": "Companies, organizations, sites, departments, teams, memberships, and directory users."},
    {"name": "fleet", "description": "Fleet registry — manufacturers, models, aircraft, registrations, and status."},
    {"name": "components", "description": "Aircraft components, serialized parts, ATA, install/remove history."},
    {"name": "publications", "description": "Technical publications metadata and revisions."},
    {"name": "technical-library", "description": "License-safe technical library browse, search, and storage."},
    {"name": "personnel", "description": "Employees, qualifications, and authorizations."},
    {"name": "maintenance", "description": "Maintenance tasks, programs, execution, certification, and technical logbook."},
    {"name": "work-orders", "description": "Work packages, work orders, and job-card execution."},
    {"name": "planning", "description": "Maintenance planning, MPD, AD/SB/EO, forecast, hangar, and workforce."},
    {"name": "logistics", "description": "Warehouses, part master, inventory, purchasing, tools, and material planning."},
    {"name": "platform", "description": "Enterprise platform foundation — identity extensions, files, search, workflow, notifications."},
    {"name": "marketplace", "description": "Digital Marketplace — sellers, products, cart, quotes, orders (payments not configured)."},
    {"name": "network", "description": "Aviation Network — org/professional profiles, partnerships, collaboration."},
    {"name": "twin", "description": "Digital Twin — twin objects, history, configuration, relationships (non-3D)."},
    {"name": "plugins", "description": "Plugin Platform — catalog, installations, dashboard layouts."},
    {"name": "event-fabric", "description": "Enterprise Event Fabric — catalog, publish, subscriptions, DLQ, replay."},
    {"name": "fabric", "description": "Universal Data Fabric / digital thread read models."},
    {"name": "ecosystem", "description": "Aviation digital ecosystem stakeholder catalogs and enrollments."},
    {"name": "connect", "description": "Mercury Connect integration endpoints."},
    {"name": "oem", "description": "OEM catalog readiness surfaces."},
    {"name": "authority", "description": "Authority portal readiness mapping. Not a certification or approval system."},
]

TAG_NORMALIZE = {"Connectors": "connectors", "org": "organizations"}

PATH_TAG_PREFIXES: list[tuple[str, str]] = [
    ("/admin", "admin"),
    ("/api/v1/auth", "auth"),
    ("/api/v1/approvals", "approvals"),
    ("/api/v1/incidents", "incidents"),
    ("/api/v1/audit", "audit"),
    ("/api/v1/reports", "reports"),
    ("/api/v1/alerts", "alerts"),
    ("/api/v1/dashboard", "dashboard"),
    ("/api/v1/decisions", "decisions"),
    ("/api/v1/integrations", "platform"),
    ("/api/v1/compliance", "platform"),
    ("/api/v1/platform", "platform"),
    ("/health", "probes"),
    ("/ready", "probes"),
    ("/live", "probes"),
    ("/metrics", "probes"),
    ("/api/v1/health", "probes"),
    ("/api/v1/ready", "probes"),
]

PUBLIC_OPS = {
    ("/health", "get"),
    ("/ready", "get"),
    ("/live", "get"),
    ("/metrics", "get"),
    ("/api/v1/health", "get"),
    ("/api/v1/ready", "get"),
    ("/api/v1/auth/login", "post"),
    ("/api/v1/auth/logout", "post"),
    ("/api/v1/auth/session", "get"),
    ("/api/v1/auth/public-config", "get"),
    ("/api/v1/auth/oidc/login", "get"),
    ("/api/v1/auth/oidc/callback", "get"),
}

JSON_OBJECT = {
    "type": "object",
    "additionalProperties": True,
    "description": "JSON object. This operation does not declare a named Pydantic response_model.",
}

ERROR_401 = {"description": "Authentication required — missing or invalid session cookie, or invalid API key."}
ERROR_403 = {"description": "Insufficient permissions for the active tenant/role."}
ERROR_404 = {"description": "Resource not found, or not visible in the active organization/site."}
ERROR_409 = {"description": "Conflict with current resource state (illegal transition or duplicate)."}
ERROR_422 = {"description": "Request validation failed (Pydantic). See `detail` for field errors."}
ERROR_429 = {"description": "Rate limited. Retry after the period in `Retry-After` when present."}

SKIP_REQUIRE_NAMES = {"require_session", "require_allowed", "get_db", "dependency"}


def _walk_calls(dependant: Any, acc: list[Any]) -> None:
    if dependant is None:
        return
    if getattr(dependant, "call", None):
        acc.append(dependant.call)
    for child in getattr(dependant, "dependencies", None) or []:
        _walk_calls(child, acc)


def _permission_doc_for_route(route: APIRoute) -> tuple[list[str], list[str]]:
    calls: list[Any] = []
    _walk_calls(getattr(route, "dependant", None), calls)
    permissions: list[str] = []
    gates: list[str] = []
    for fn in calls:
        name = getattr(fn, "__name__", "") or ""
        if name.startswith("require_") and name not in SKIP_REQUIRE_NAMES:
            gates.append(name)
        for cell in getattr(fn, "__closure__", None) or ():
            value = cell.cell_contents
            if isinstance(value, tuple) and value and all(isinstance(item, str) for item in value):
                for item in value:
                    if item not in permissions:
                        permissions.append(item)
    return permissions, gates


def collect_permission_docs(app: Any) -> dict[tuple[str, str], tuple[list[str], list[str]]]:
    """Map OpenAPI (path, method) to (permission strings, require_* gate names)."""
    found: dict[tuple[str, str], tuple[list[str], list[str]]] = {}

    def consider(route: APIRoute, prefix: str = "") -> None:
        path = route.path
        if prefix and not path.startswith(prefix):
            joined = prefix.rstrip("/") + path
        else:
            joined = path
        docs = _permission_doc_for_route(route)
        for method in route.methods or []:
            if method in {"HEAD", "OPTIONS"}:
                continue
            found[(joined, method.lower())] = docs

    for item in app.routes:
        if isinstance(item, APIRoute):
            consider(item)
        elif type(item).__name__ == "_IncludedRouter":
            router = item.original_router
            prefix = str(getattr(router, "prefix", "") or "")
            for route in router.routes:
                if isinstance(route, APIRoute):
                    consider(route, prefix)
    return found


def _tag_for_path(path: str) -> str:
    for prefix, tag in PATH_TAG_PREFIXES:
        if path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "{"):
            return tag
        if prefix in {"/health", "/ready", "/live", "/metrics"} and path == prefix:
            return tag
    if path.startswith("/api/v1/health") or path.startswith("/api/v1/ready"):
        return "probes"
    return "platform"


def _is_public(path: str, method: str) -> bool:
    return (path, method) in PUBLIC_OPS


def _ensure_json_response(op: dict[str, Any], code: str = "200") -> None:
    responses = op.setdefault("responses", {})
    current = responses.get(code)
    if not isinstance(current, dict):
        responses[code] = {
            "description": "Successful response",
            "content": {"application/json": {"schema": JSON_OBJECT}},
        }
        return
    content = current.setdefault("content", {})
    json_content = content.setdefault("application/json", {})
    if not json_content.get("schema") and "text/plain" not in content:
        json_content["schema"] = JSON_OBJECT


def _build_description(
    path: str,
    method: str,
    existing: str,
    permissions: list[str],
    gates: list[str],
) -> str:
    parts: list[str] = []
    if existing.strip():
        parts.append(existing.strip())
    if _is_public(path, method):
        if path.endswith("/auth/login"):
            parts.append(
                "Public (rate-limited). Sets an HttpOnly session cookie on success. "
                "Does not issue JWT access or refresh tokens."
            )
        elif path.endswith("/auth/logout"):
            parts.append("Public and idempotent. Deletes the server-side session and cookie when present.")
        elif path.endswith("/auth/session"):
            parts.append("Public. Always HTTP 200; `authenticated` is true or false.")
        elif path.endswith("/auth/public-config"):
            parts.append("Public. Auth mode, SSO availability, and SIM workspace visibility. No secrets.")
        elif path.endswith("/auth/oidc/login"):
            parts.append(
                "Public (rate-limited). Redirects to the identity provider (authorization-code + PKCE). "
                "Fails closed with HTTP 503 if OIDC is not configured."
            )
        elif path.endswith("/auth/oidc/callback"):
            parts.append(
                "Public (rate-limited). Completes authorization-code + PKCE, maps the IdP subject onto a "
                "provisioned directory user, and sets the HttpOnly session cookie."
            )
        else:
            parts.append("Public probe. No session cookie required.")
    else:
        parts.append(
            "Authentication: HttpOnly session cookie (`SessionCookie`) or optional machine "
            "`X-API-Key` / `Authorization: Bearer` when `MERCURY_API_KEY` is configured."
        )
        parts.append(
            "Tenant: organization and site are taken from the session. "
            "Cross-tenant identifiers return 404 or 403."
        )
        if permissions:
            parts.append("Required permission(s): " + ", ".join(permissions) + ".")
        elif gates:
            parts.append("Authorization gate: " + ", ".join(gates) + ".")
        else:
            parts.append("Authorization is enforced server-side (session RBAC).")
    parts.append("Validation: query, path, and JSON bodies are checked by Pydantic (HTTP 422 on failure).")
    # Preserve order, drop exact duplicates.
    seen: set[str] = set()
    unique: list[str] = []
    for part in parts:
        if part not in seen:
            seen.add(part)
            unique.append(part)
    return " ".join(unique)


def enrich_openapi(schema: dict[str, Any], app: Any) -> dict[str, Any]:
    schema["info"] = schema.get("info") or {}
    schema["info"]["description"] = (
        "Mercury AEOS REST API (`/api/v1`). Operator authentication is an opaque HttpOnly "
        "session cookie, not JWT. Optional machine auth uses `X-API-Key` when configured. "
        "Domain data is organization/site scoped. Operational connector feeds may be simulated. "
        "Interactive docs: `/docs` (Swagger UI) and `/redoc`. "
        "WebSocket notifications: `GET /api/v1/ws` (session cookie required; not listed as a REST operation)."
    )
    schema["servers"] = [{"url": "/", "description": "Same-origin (NGINX or local backend)"}]

    tags_by_name = {item["name"]: item for item in OPENAPI_TAGS}
    existing_tags = schema.get("tags") or []
    for item in existing_tags:
        name = TAG_NORMALIZE.get(item.get("name") or "", item.get("name") or "")
        if name and name not in tags_by_name:
            tags_by_name[name] = {"name": name, "description": (item.get("description") or "").strip() or name}
        elif name in tags_by_name and (item.get("description") or "").strip() and name not in {t["name"] for t in OPENAPI_TAGS}:
            pass
    schema["tags"] = [tags_by_name[name] for name in sorted(tags_by_name)]

    components = schema.setdefault("components", {})
    schemes = components.setdefault("securitySchemes", {})
    schemes["SessionCookie"] = {
        "type": "apiKey",
        "in": "cookie",
        "name": settings.session_cookie_name,
        "description": (
            "Opaque HttpOnly session cookie issued by POST /api/v1/auth/login. "
            "JWT access/refresh tokens are not issued or accepted as operator sessions."
        ),
    }
    schemes["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": (
            "Optional machine authentication when MERCURY_API_KEY is set. "
            "Alternative header: Authorization Bearer <same key> (not JWT validation)."
        ),
    }

    perm_map = collect_permission_docs(app)
    login_example = {"operator": "operator", "password": "your-password"}

    for path, methods in (schema.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.startswith("x-") or not isinstance(op, dict):
                continue
            key = (path, method.lower())
            permissions, gates = perm_map.get(key, ([], []))

            tags = [TAG_NORMALIZE.get(tag, tag) for tag in (op.get("tags") or [])]
            if not tags:
                tags = [_tag_for_path(path)]
            op["tags"] = tags

            if not (op.get("summary") or "").strip():
                op["summary"] = (op.get("operationId") or f"{method} {path}").replace("_", " ")

            op["description"] = _build_description(
                path, method, str(op.get("description") or ""), permissions, gates
            )

            responses = op.setdefault("responses", {})
            if method != "delete":
                success_code = "201" if "201" in responses else "200"
                if success_code not in responses:
                    responses[success_code] = {"description": "Successful response"}
                _ensure_json_response(op, success_code if success_code in responses else "200")
                # Metrics may be text/plain — leave existing content.
                if path.rstrip("/").endswith("/metrics"):
                    responses["200"] = {
                        "description": "Prometheus text exposition (404 if metrics disabled).",
                        "content": {"text/plain": {"schema": {"type": "string"}}},
                    }

            if _is_public(path, method):
                op.pop("security", None)
                if path.endswith("/auth/login") or "/auth/oidc/" in path:
                    responses["429"] = ERROR_429
                if path.endswith("/auth/login"):
                    responses["401"] = {"description": "Invalid credentials."}
                    responses["429"] = ERROR_429
                    body = (op.get("requestBody") or {}).get("content") or {}
                    app_json = body.get("application/json")
                    if isinstance(app_json, dict):
                        app_json.setdefault("example", login_example)
                if path.endswith("/auth/oidc/login"):
                    responses["503"] = {"description": "OIDC is not configured or the provider is unreachable."}
                if path.endswith("/auth/oidc/callback"):
                    responses["401"] = {"description": "Invalid or expired OIDC state, or the identity provider denied authentication."}
                    responses["403"] = {"description": "Identity is not provisioned or the account is disabled."}
                    responses["503"] = {"description": "OIDC is not configured or the provider is unreachable."}
            else:
                op["security"] = [{"SessionCookie": []}, {"ApiKeyAuth": []}]
                responses.setdefault("401", ERROR_401)
                responses.setdefault("403", ERROR_403)
                if "{" in path:
                    responses.setdefault("404", ERROR_404)
                if method in {"post", "patch", "put", "delete"}:
                    responses.setdefault("409", ERROR_409)
            responses.setdefault("422", ERROR_422)

    return schema
