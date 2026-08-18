# API Documentation (RC1 Blocker — OpenAPI)

**Status:** Implemented / verified 2026-08-17  
**Parent:** Mercury Platform RC1 Release Blocker Report (workflow 21 — API Documentation)

## Surfaces

| URL | Use |
|-----|-----|
| `/openapi.json` | Generated OpenAPI 3 specification (source of truth) |
| `/docs` | Swagger UI (customer demonstration) |
| `/redoc` | ReDoc |

Operator auth is documented as `SessionCookie` (HttpOnly cookie). Optional machine auth is `ApiKeyAuth` (`X-API-Key`). JWT access/refresh tokens are **not** part of the contract. WebSocket `GET /api/v1/ws` requires the same cookie and is described in the spec `info` block (not a REST path).

## What is documented per operation

Generated from FastAPI routers, then enriched by `backend/app/openapi_docs.py` (documentation only — no behavior change):

- **Summary** — first-line docstring / function name
- **Description** — authentication, tenant scope, permission strings or `require_*` gate, Pydantic validation
- **Tag** — one catalog tag with a description (including previously untagged Command routes)
- **Security** — session cookie or API key on protected routes; public probes/login/logout/session have none
- **Errors** — `401`/`403` on protected routes; `404` when the path has parameters; `409` on mutations; `422` validation; login also documents `429`
- **Success schema** — named Pydantic `response_model` where declared; otherwise an explicit JSON object schema

## Missing documentation report (residual)

These items are **not** RC blockers for `/docs` demonstration. They are honest gaps:

| Gap | Detail |
|-----|--------|
| Named response models | A minority of Command/auth/probe operations return dicts; OpenAPI now types them as generic objects rather than named models |
| Per-field examples | Most Pydantic fields have types/constraints; only login (and similar) carry a request example |
| WebSocket | `/api/v1/ws` is not a REST operation in Swagger |
| In-app explorer | UX has no embedded OpenAPI browser; use `/docs` |
| Production exposure | `/docs` should be edge-restricted in production (API Standards §10.3) |

## Consistency

Router `tags=` values are lowercase kebab-case (`connectors` not `Connectors`). Duplicate unused `org` tag removed from the catalog in favor of `organizations`.

## Tests

`backend/tests/test_rc1_api_documentation.py` — `/docs` and `/redoc` load; every operation has summary, description, tag, validation text, security, and error responses; tag catalog covers all used tags.
