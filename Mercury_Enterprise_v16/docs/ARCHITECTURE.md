# Architecture

## Runtime

Browser → NGINX frontend → FastAPI API → PostgreSQL/SQLite

The browser opens same-origin `/api/v1` and `/api/v1/ws` (via NGINX) for API and live event notifications. FastAPI broadcasts incident creation, status, timeline, and heartbeat messages.

Optional local dual-process demos may override API/WS bases with `frontend/js/config.local.js` (`window.__MERCURY_API_BASE__` / `window.__MERCURY_WS_URL__`).

## Local mode

The Windows launchers use SQLite and Python's local HTTP server for low-friction development. `START_FRONTEND.bat` creates `config.local.js` so `:3000` can reach `:8000` without NGINX.

## Container mode

Docker Compose uses PostgreSQL, a **single-worker** FastAPI container (in-memory sessions), and NGINX. Backend port `8000` is exposed on the Compose network only. Scale-out requires a shared session store (not in this RC).

## Modules

- `backend/app/core`: configuration, logging, shared health helpers
- `backend/app/security`: RBAC permissions
- `backend/app/websocket`: connection management
- `backend/app/models.py`: persistence models (incidents, evidence, audit_events)
- `backend/app/schemas.py`: API contracts
- `backend/app/decision`: advisory DecisionEngine, scoring, explanations, in-memory review store
- `backend/app/audit.py` / `reporting.py` / `connectors/`: accountability, analytics, lifecycle
- `backend/alembic`: Postgres migration baseline (`alembic upgrade head`)
- `frontend/js`: modular operator workspaces and simulation (vanilla JS only)

## Milestone 2 extensions

- Task 19: `/api/v1/decisions*` explainability and human review; Command Decision Timeline panels
- Task 20: enriched `/health` `/ready` `/platform/status` `/ops/health`; runbooks under `docs/runbooks/`

## Production hardening

See `docs/design/PRODUCTION_HARDENING_SPEC.md` for packaging, authz, and deployment hardening applied after V2.0 RC gate NO GO.
