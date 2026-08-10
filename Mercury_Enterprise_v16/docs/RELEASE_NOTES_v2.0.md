# Mercury Enterprise — Release Notes v2.0

| Field | Value |
|-------|--------|
| **Release** | Mercury Enterprise **V2.0** (engineering / pilot) |
| **Package / API version** | `16.0.0` |
| **Status** | Hardened release candidate — **READY FOR RELEASE** pending final tag approval |
| **Branch** | `task-16-audit-provenance` |
| **Roadmap ceiling** | APPLY_TASK through **Task 20** |
| **Validation** | Backend tests **81 passed**; frontend `node --check` PASS; see design verification docs |
| **Merge / tag** | Not performed until explicit approval after verification |

> **Safety notice:** UAV, aircraft, radar/RF/EO/thermal, AI assessments, weather, compliance, and mission data are **simulated or advisory**. Do not use for live safety or security decisions without independent validation and authorized integrations.

---

## Completed features

### Platform foundations
- FastAPI REST API with request IDs, timing headers, CORS allow-list, structured logging
- Vanilla JS modular frontend (Command, Radar, Digital Twin–style, Executive, History, Admin, Cloud, Integrations, Compliance)
- WebSocket live gateway (`/api/v1/ws`) with heartbeat and incident-related broadcasts
- SQLAlchemy persistence: SQLite (local/dev) and PostgreSQL (Compose)
- Alembic baseline migrations for Postgres (`backend/alembic`)
- Dockerfiles, Docker Compose, NGINX reverse-proxy reference layout
- Windows launchers (`START_ALL.bat`, `CHECK_SYSTEM.bat`, `STOP_MERCURY.bat`)
- Operator / administrator / deploy-upgrade-rollback / disaster-recovery runbooks

### Milestone 1–2
- Audit logging & evidence provenance
- Historical reporting & analytics
- Connector lifecycle & resilience
- AI explainability & decision review (`/decisions*`, human approval required)
- Production observability (`/health`, `/ready`, `/platform/status`, `/ops/health`)

### Production hardening (post-RC gate)
- Same-origin API (`/api/v1`) and WebSocket via NGINX; optional `config.local.js` for dual-process local demos
- Backend Docker `--workers 1` (in-memory sessions)
- Git-root GitHub Actions workflow
- Session RBAC on incident/alert/dashboard/platform/ops reads; ops coordinate authenticated
- Interactive operator sign-in (no embedded demo auto-login)
- **No embedded default password** — `MERCURY_AUTH_PASSWORD` required; forbidden demo values rejected at startup
- `.env.example` template; SQLite runtime DBs gitignored / removed from the repository tip

---

## Architecture summary

```text
Browser → NGINX (:3000) → FastAPI (compose network :8000) → SQLite | PostgreSQL
              ↘ same-origin /api/v1/ws
```

---

## API summary

Base: `/api/v1`. Public probes only: `GET /health`, `GET /ready`. All other operational routes require session + RBAC as documented in OpenAPI (`/docs`).

Key groups: auth, incidents (site-scoped reads), decisions, reports, audit, connectors, ops, dashboard, alerts, WebSocket `/ws`.

---

## Database summary

Durable tables: `incidents`, `timeline_events`, `evidence`, `audit_events`.  
Postgres: run `alembic upgrade head` for managed upgrades. SQLite: `create_all` for empty local DBs.  
Runtime `*.db` files are **not** part of the release tree.

---

## Breaking changes (vs pre-hardening RC)

- Anonymous incident/alert/dashboard/platform/ops reads now return **401/403**
- `MERCURY_AUTH_PASSWORD` **must** be set; no `mercury-demo` default
- Frontend defaults to same-origin `/api/v1` (local dual-process needs `config.local.js`)
- Backend container uses **one** uvicorn worker

Additive Milestone 1–2 APIs remain compatible for authenticated clients.

---

## Deployment steps

1. Copy `.env.example` → `.env`; set a unique `MERCURY_AUTH_PASSWORD` (≠ forbidden demo values; ≥12 chars if `MERCURY_ENV=production`)
2. `docker compose up --build`
3. Open `http://localhost:3000`, sign in, verify `/api/v1/ready` via NGINX
4. Optional Postgres: `cd backend && alembic upgrade head`

Local Windows: set password in `.env`, run `START_ALL.bat` (creates `config.local.js` for `:8000` API).

---

## Rollback steps

1. Redeploy previous known-good commit/tag  
2. Restore DB backup only if needed  
3. Do not delete `audit_events` to “fix” bugs  
4. Confirm `/ready` and login  

---

## Known limitations

- Simulated sensors/AI — not certified for live ops  
- In-memory sessions/decisions — single worker only  
- Shared-password auth (no OIDC/SSO yet)  
- Incident **write** IDOR hardening across sites recommended for multi-tenant (see RC2 action plan)  

---

## Production checklist

- [x] Hardening phases 1–4 implemented  
- [x] Backend tests green (80)  
- [x] Frontend JS syntax checks  
- [x] No embedded demo password default  
- [x] Release notes current for V2.0 / 16.0.0  
- [ ] Docker Compose smoke on release host (record in verification)  
- [ ] GitHub Actions green after push  
- [ ] Explicit tag/merge approval  

---

## Related documents

`docs/design/PRODUCTION_HARDENING_REPORT.md`, `RC2_FINAL_ACTION_PLAN.md`, `FINAL_RELEASE_VERIFICATION.md`, `FINAL_RELEASE_VERIFICATION_v2.md`
