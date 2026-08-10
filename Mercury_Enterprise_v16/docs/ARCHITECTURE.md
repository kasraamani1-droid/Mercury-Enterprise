# Architecture

## Runtime

Browser → NGINX frontend → FastAPI API → PostgreSQL/SQLite

The browser also opens `/api/v1/ws` for live event notifications. FastAPI broadcasts incident creation, status, timeline, and heartbeat messages.

## Local mode

The Windows launchers use SQLite and Python's local HTTP server for low-friction development.

## Container mode

Docker Compose uses PostgreSQL, a multi-worker FastAPI container, and NGINX. The architecture is intentionally simple enough for a pilot while leaving clean seams for Redis, task workers, object storage, OIDC, and telemetry.

## Modules

- `backend/app/core`: configuration, logging, shared health helpers
- `backend/app/security`: API write protection and RBAC permissions
- `backend/app/websocket`: connection management
- `backend/app/models.py`: persistence models (incidents, evidence, audit_events)
- `backend/app/schemas.py`: API contracts
- `backend/app/decision`: advisory DecisionEngine, scoring, explanations, in-memory review store
- `backend/app/audit.py` / `reporting.py` / `connectors/`: accountability, analytics, lifecycle
- `frontend/js`: modular operator workspaces and simulation (vanilla JS only)

## Milestone 2 extensions

- Task 19: `/api/v1/decisions*` explainability and human review; Command Decision Timeline panels
- Task 20: enriched `/health` `/ready` `/platform/status` `/ops/health`; runbooks under `docs/runbooks/`
