# Architecture

## Runtime

Browser → NGINX frontend → FastAPI API → PostgreSQL/SQLite

The browser also opens `/api/v1/ws` for live event notifications. FastAPI broadcasts incident creation, status, timeline, and heartbeat messages.

## Local mode

The Windows launchers use SQLite and Python's local HTTP server for low-friction development.

## Container mode

Docker Compose uses PostgreSQL, a multi-worker FastAPI container, and NGINX. The architecture is intentionally simple enough for a pilot while leaving clean seams for Redis, task workers, object storage, OIDC, and telemetry.

## Modules

- `backend/app/core`: configuration and logging
- `backend/app/security`: API write protection
- `backend/app/websocket`: connection management
- `backend/app/models.py`: persistence models
- `backend/app/schemas.py`: API contracts
- `frontend/js`: modular operator workspaces and simulation
