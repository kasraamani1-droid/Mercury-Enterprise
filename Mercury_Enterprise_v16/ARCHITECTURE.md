# Architecture

## Runtime

```
Browser / Operator UI
        │
   NGINX (frontend container; edge TLS optional)
        │
   FastAPI (single worker)
        │
 PostgreSQL or SQLite
```

The browser uses same-origin `/api/v1` and `/api/v1/ws` (via NGINX) for API and live events. FastAPI broadcasts incident, timeline, and heartbeat messages.

Optional local dual-process demos may override API/WS bases with `frontend/js/config.local.js`.

## Local mode

Windows launchers use SQLite and Python's local HTTP server. `START_FRONTEND.bat` creates `config.local.js` so `:3000` can reach `:8000` without NGINX.

## Container mode

Docker Compose provides:

| Service | Role |
|---------|------|
| `postgres` | Persistent database |
| `backend` | FastAPI API (Compose-network only) |
| `frontend` | Static UI + `/api` reverse proxy on `:3000` |
| `nginx` + `certbot` | Production profile — edge HTTPS / Let's Encrypt |

Backend port `8000` is **not** published on the host in production Compose. Scale-out requires a shared session store (not in this release).

## Modules

| Area | Location |
|------|----------|
| Config / logging / health / metrics | `backend/app/core/` |
| RBAC, rate limit, operators | `backend/app/security/` |
| Organizations / multi-tenancy | `backend/app/org/` |
| Aircraft registry / fleets | `backend/app/fleet/` |
| Aircraft components / configuration | `backend/app/components/` |
| Publications / technical library | `backend/app/publications/` |
| Personnel / qualifications | `backend/app/personnel/` |
| Maintenance task engine / certification / logbook | `backend/app/maintenance/` |
| WebSocket manager | `backend/app/websocket/` |
| Persistence models | `backend/app/models.py` |
| API contracts | `backend/app/schemas.py` |
| Decision engine (advisory) | `backend/app/decision/` |
| Audit / reporting / connectors | `backend/app/audit.py`, `reporting.py`, `connectors/` |
| Admin ops API | `backend/app/routers/admin.py` |
| Alembic migrations | `backend/alembic/` |
| Operator UI (vanilla JS) | `frontend/js/` |

## Cross-cutting concerns

- **Auth:** Session cookie + server-side RBAC (Administrator / Operator / Reviewer / Viewer)
- **Organizations:** Persisted company → organization → site → department → team hierarchy with membership-scoped context switches (see [docs/ORGANIZATIONS.md](docs/ORGANIZATIONS.md))
- **Fleet registry:** Shared manufacturer/model/status catalog plus org-scoped operators, fleets, aircraft, and registrations (see [docs/FLEET_REGISTRY.md](docs/FLEET_REGISTRY.md))
- **Components:** ATA catalog, serialized components, install/remove/transfer history, and aircraft configuration (see [docs/AIRCRAFT_CONFIGURATION.md](docs/AIRCRAFT_CONFIGURATION.md))
- **Publications / technical library:** Org-scoped publication metadata, immutable revisions, license-safe storage locators, ATA/catalog/model/family linkage (see [docs/PUBLICATIONS.md](docs/PUBLICATIONS.md), [docs/TECHNICAL_LIBRARY.md](docs/TECHNICAL_LIBRARY.md))
- **Personnel & certification:** Employees, qualifications, ACA authorizations, digital stamps/signatures, critical-task workflows, technical logbook (see [docs/PERSONNEL.md](docs/PERSONNEL.md), [docs/MAINTENANCE_TASKS.md](docs/MAINTENANCE_TASKS.md), [docs/MAINTENANCE_CERTIFICATION.md](docs/MAINTENANCE_CERTIFICATION.md), [docs/RBAC.md](docs/RBAC.md))
- **AI-ready (not implemented):** Document index / embedding / knowledge cross-ref stubs under maintenance APIs — no RAG/OCR in this release
- **Observability:** JSON logs, `/health` `/ready` `/live`, Prometheus `/metrics`, admin audit APIs
- **Security edge:** TLS 1.2+, security headers, rate limits (see [SECURITY.md](SECURITY.md))

## Target platform (future)

A longer-term multi-service shape (API gateway, Redis, object store, message queue, mobile clients) is documented as **deferred** in [ROADMAP.md](ROADMAP.md). Current releases remain an additive FastAPI + NGINX foundation.

## Related

- [INSTALL.md](INSTALL.md) · [DEPLOYMENT.md](DEPLOYMENT.md) · [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)
- Design history: `docs/design/`
