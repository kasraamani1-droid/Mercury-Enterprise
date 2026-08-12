# Mercury Enterprise — Final Release Audit

**Product:** Mercury Enterprise V2.0 (package label v16)  
**Audit date:** 2026-08-10  
**Branch audited:** `task-16-audit-provenance` (HEAD includes Milestone 2 through `3e4b306`)  
**Git root:** `C:\Users\14383\Downloads\Mercury_Enterprise_v16`  
**Package path:** `Mercury_Enterprise_v16/`  
**Mode:** Read-only — **no code modified**  
**APPLY_TASK ceiling:** Task 20 is the final in-repo apply-task (no Tasks 21–25)

---

## Executive verdict

Mercury is a **coherent engineering Release Candidate / reference demo platform** (vanilla JS + FastAPI + SQLite/Postgres). It is **not certified for live operational or safety use**.

| Lens | Score (0–100) | Interpretation |
|------|---------------|----------------|
| Engineering RC / internal demo | **72** | Runnable locally; M1/M2 features present; pytest depth good |
| Production / internet-exposed deploy | **38** | Authz gaps, multi-worker sessions, compose/frontend URL mismatch, CI path |
| **Overall production readiness** | **48** | Weighted toward production exposure risk |

---

## 1. Architecture review

### Intended shape

```text
Browser → NGINX (frontend) → FastAPI → SQLite (local) | PostgreSQL (Compose)
                ↘ WebSocket /api/v1/ws
```

### Actual strengths

- Clear separation: FastAPI backend, vanilla JS frontend, no SPA framework creep.
- Domain modules exist and are reused: missions, alerts, timeline, fusion, decision, connectors, audit, reporting, ops.
- Milestone 1–2 additive extensions preserved Tasks 12–15 contracts.
- Human-control / advisory decision model is explicit in APIs and UI copy.

### Architectural risks

| Issue | Severity |
|-------|----------|
| Frontend hardcodes `http://127.0.0.1:8000` and WS `:8000`, bypassing nginx `/api` proxy | Critical |
| Dual EventBus implementations (`core/event_bus.py` vs `events/bus.py`) | Medium |
| Ops router instantiates a **separate** `ResponseOrchestrationService` vs `main.py` singleton | High |
| Large `main.py` monolith hosts most routes (maintainability) | Medium |
| Nested package under git root complicates CI/docs paths | High |
| Version naming drift (v10 / v15 / v16 / V2.0 across bats, README, UI, `.env.example`) | Medium |

### APPLY_TASK roadmap status

- Final apply-task file: **`APPLY_TASK_20.md`** (Module 15 — production observability/packaging).
- Missing files: `APPLY_TASK_1.md`, `APPLY_TASK_3.md` (historical gaps); **no 21+**.
- V2.0 apply-task roadmap is **complete** at Task 20.

---

## 2. Backend review

### Surface area

| Area | Location | Notes |
|------|----------|-------|
| Entry | `backend/app/main.py` | Auth, incidents, decisions, dashboard, WS, most APIs |
| Routers | `routers/connectors.py`, `routers/ops.py` | Connector lifecycle; ops health/coordinate |
| Engines | `decision/`, `missions/`, `fusion/`, `ops/`, `ai/`, `alerts.py`, `timeline/` | Mostly in-memory |
| Persistence helpers | `models.py`, `database.py`, `audit.py`, `reporting.py` | SQLAlchemy |
| Security | `security/authorization.py`, `security/api_key.py` | RBAC used; API key **unused** |
| Observability | `core/health.py`, `core/logging.py` | Milestone 2 |

### Positive findings

- Decision evaluate/review gated by `decisions.read` / `decisions.review`.
- Audit, reports, connector manage paths are session + permission aware.
- Health/ready enriched with checks; ready fails on DB loss.
- Advisory metadata enforced (`requires_human_approval`, `automatic_execution=false`).

### Negative findings

| Finding | Severity |
|---------|----------|
| `GET /incidents`, `/{id}`, `/assessment`, `/report` lack `require_session` | Critical |
| `GET /alerts`, optional dashboard access without forced auth | High |
| `POST /ops/coordinate` unauthenticated | Critical |
| In-memory `_sessions` incompatible with Dockerfile `--workers 2` | Critical |
| `require_api_key` never wired to routes | High |
| Incident mutations by ID without org/site ownership check (IDOR) | High |
| Approvals / decisions / alerts / sessions not durable across restart/workers | High |
| Sync SQLAlchemy on default event loop under multi-worker load | Medium |

---

## 3. Frontend review

### Structure

- **18** ES modules under `frontend/js/` (entry `app.js`).
- Workspaces: command, digitalTwin, radar, executive, history, admin, cloud, integrations, compliance.
- API client: `api.js` with credentials + abort timeout.

### Critical / high issues

| Finding | Path | Severity |
|---------|------|----------|
| Hardcoded `API_BASE = "http://127.0.0.1:8000/api/v1"` | `frontend/js/config.js` | Critical |
| WebSocket to host `:8000` (breaks Compose where backend is not published) | `frontend/js/websocket.js` | Critical |
| Auto-login `operator` / `mercury-demo` | `frontend/js/app.js` `ensureSession` | Critical |
| XSS risk: unescaped `innerHTML` in audit/history/org-site/timeline/connectors | `enterprise.js`, `app.js`, `enterprise8.js` | High |
| Many surfaces simulated (copilot, fusion matrix, cloud/compliance KPIs) | multiple | High (ops misread risk) |
| Duplicate `esc` / `escapeHtml` / `download` helpers | utils vs app / enterprise vs enterprise8 | Medium |
| Leaflet CDN without SRI | `index.html` | Medium |

### Positive findings

- Decision explain/review UI is additive inside Command (no second app).
- Several modules (`incidents.js`, `assessment.js`, `eventLog.js`) use `esc()`.
- Integrations lifecycle binds to real connector APIs (Task 18).

---

## 4. Database review

### Durable tables (`models.py`)

| Table | Purpose |
|-------|---------|
| `incidents` | Incidents + optional org/site |
| `timeline_events` | Incident timeline |
| `evidence` | Evidence + provenance + org/site |
| `audit_events` | Durable audit trail |

### Not durable (process memory)

Sessions, approvals, DecisionEngine store, AlertManager, TimelineManager rings, fusion tracks, connector health history, org/site catalogs.

### Migration / ops

| Finding | Severity |
|---------|----------|
| No Alembic; `create_all` + SQLite-only ALTER guards | High for Postgres upgrades |
| Postgres path skips SQLite ALTER logic → schema drift risk | High |
| Local `mercury.db` tracked/dirty from test runs | Medium |
| Audit list filters by retention but does not purge | Medium |
| Seed backfill for missing seed evidence (M2) | Positive |

---

## 5. Security review

### Critical

1. Unauthenticated incident/assessment/report reads.  
2. Unauthenticated `POST /api/v1/ops/coordinate`.  
3. Multi-worker in-memory sessions break auth in Docker.  
4. Shared default password `mercury-demo` + frontend auto-login.

### High

5. Documented API-key write protection not enforced.  
6. Cross-site IDOR on incident resources by ID.  
7. Plaintext password equality (no hash / not constant-time).  
8. Compose Postgres password `mercury` hardcoded.  
9. XSS via unescaped DOM HTML on several admin/history/decision paths.  
10. Any authenticated user can switch to any catalog org/site.

### Medium / low

- Cookie `secure` default false (local OK; prod must set env).  
- No login rate limit / lockout.  
- Failed logins not audited.  
- CORS misconfiguration risk if origins widened carelessly.  
- Admin UI “role simulation” ≠ server RBAC roles.

### Positive

- Session cookie httponly; WS requires session.  
- RBAC matrix exists and is used on write/decision/audit/report/connector manage paths.  
- Decision outputs remain advisory.  
- No SQL injection found in static health/`ensure_schema` SQL.

---

## 6. Performance review

| Finding | Severity |
|---------|----------|
| `GET /incidents` returns unbounded full table | High |
| Reporting summary/history can load large unscoped windows into memory | High |
| Dashboard pulls all incidents + large alert slices | Medium |
| Approvals dict unbounded | Medium |
| Bounded rings elsewhere (timeline/alerts/decisions/connectors) — good | Info |
| Sync DB handlers block workers under concurrency | Medium |
| Heartbeat WS every 5s — acceptable for demo scale | Low |

**Demo scale:** adequate. **Multi-tenant production scale:** not validated; no load tests in CI.

---

## 7. CI/CD review

| Finding | Severity |
|---------|----------|
| Workflow lives at `Mercury_Enterprise_v16/.github/workflows/ci.yml` — **GitHub only loads `<repo-root>/.github/workflows/`** | Critical |
| Repo root has **no** `.github/` → CI likely **never runs on GitHub** | Critical |
| CI content (when run locally/nested): pytest, compileall, 4× `node --check`, optional `docker compose config` | Medium (incomplete) |
| Only 4/18 frontend JS files syntax-checked | High |
| Compose `continue-on-error: true` masks packaging failures | Medium |
| Backend Dockerfile uses `--workers 2` with in-memory sessions | Critical |
| Frontend nginx proxy correct; browser JS bypasses it | Critical |
| `.env.example` version/auth/TLS cookie gaps | High |

---

## 8. Testing summary

### Backend (`pytest`)

| File | Approx. tests |
|------|----------------|
| `test_api.py` | 14 |
| `test_audit.py` | 10 |
| `test_decisions_api.py` | 7 |
| `test_decision_engine.py` | 7 |
| `test_observability.py` | 7 |
| `test_connectors.py` | 5 |
| `test_reporting.py` | 4 |
| `test_alerts.py` / `test_timeline.py` / `test_fusion.py` | 3 each |
| `test_missions.py` / `test_ops.py` / `test_ai.py` | 2 each |
| **Total collected** | **~69** |

Last gate: **69 passed** (+ compileall + selected `node --check`).

### Coverage

- No `pytest-cov` / coverage threshold configured.  
- Qualitative coverage: strong on decisions, audit, reports, connectors, health.  
- Weak/absent: authz negative tests for open GETs, XSS, compose smoke, multi-worker sessions, frontend e2e.

### Frontend

- **No** unit/integration/e2e suite.  
- Syntax-only checks for a subset of modules.

---

## 9. Technical debt

1. In-memory sessions / approvals / decision reviews.  
2. Dual event buses and split ops orchestrator instance.  
3. API key module dead; docs overclaim write protection.  
4. Incident list unscoped; incomplete tenant enforcement.  
5. No Alembic / Postgres migration story.  
6. Hardcoded API/WS URLs.  
7. Nested CI path.  
8. Simulated feeds labeled inconsistently vs “enterprise” surfaces.  
9. Version string sprawl (v10/v15/v16/V2.0).  
10. No metrics endpoint (intentionally deferred).  
11. No frontend automated tests.  
12. Tracked/dirty local SQLite artifacts.  
13. `tmp_models.txt` / `tmp_schemas.txt` junk files.  
14. Empty `frontend/js/modules/` scaffolding.

---

## 10. Dead code

| Item | Notes | Severity |
|------|-------|----------|
| `backend/app/security/api_key.py` | Never depended on by routes | Medium |
| `settings.api_key` / `metrics_enabled` | Config without enforcement/feature | Medium |
| `tmp_models.txt`, `tmp_schemas.txt` | Root junk | Low |
| Empty `frontend/js/modules/` | Unused | Low |
| Possible unused imports in `main.py` (e.g. ops health builder if only used in router) | Low | Low |

---

## 11. Duplicate code

| Pattern | Locations | Severity |
|---------|-----------|----------|
| Separate ops orchestrator vs app singleton | `main.py` vs `routers/ops.py` | High |
| Dual EventBus stacks | `core/event_bus.py` vs `events/bus.py` | Medium |
| Async publish boilerplate | decision / ops / missions | Medium |
| HTML escape helpers | `utils.esc` vs `app.escapeHtml` | Medium |
| `download()` helpers | `enterprise.js` vs `enterprise8.js` | Low |
| Overlapping health payload builders | `core/health.py` | Low (acceptable DRY helper) |
| Confidence naming overlap | `ai/confidence.py` vs `fusion/confidence.py` | Low (different domains) |

---

## 12. TODO / FIXME inventory

| Scope | Result |
|-------|--------|
| Backend `*.py` | **No `TODO` / `FIXME` / `XXX` / `HACK` markers** |
| Frontend `*.js` / `*.html` | **None** |
| Docs | Policy text in `AI_ENGINEERING_WORKFLOW.md` discouraging TODO stubs; readiness “still required” lists are intentional backlog, not code TODOs |
| Design specs | Checklist items in Milestone docs (process), not runtime debt markers |

---

## 13. Dependency review

### `backend/requirements.txt`

```text
fastapi>=0.128,<1
uvicorn[standard]>=0.48,<1
sqlalchemy>=2.0,<3
pydantic>=2.13,<3
psycopg[binary]>=3.2,<4
pytest>=9,<10
httpx>=0.28,<1
```

| Finding | Severity |
|---------|----------|
| Lower-bound pins only; **no lockfile** | Medium |
| No Dependabot / `pip-audit` in CI | Medium |
| Python 3.13 in Dockerfile/CI — verify deploy OS wheel support | Low |
| Frontend: **no** `package.json` (vanilla JS + CDN Leaflet) | Info |
| CDN third-party without SRI/pinning | Medium |

---

## 14. Production readiness score

### Category scores (0–100)

| Category | Score | Rationale |
|----------|------:|-----------|
| Architecture fit (RC/demo) | 80 | Coherent stack; additive milestones |
| Feature completeness (Tasks 12–20) | 85 | Roadmap complete at Task 20 |
| Security | 28 | Open reads, demo auth, multi-worker sessions, XSS |
| Data durability / tenancy | 45 | Audit durable; sessions/approvals/decisions not |
| Observability / ops docs | 70 | Health/ready/runbooks present |
| CI/CD reliability | 25 | Workflow not at git root; incomplete frontend gates |
| Testing depth | 60 | Strong backend pytest; weak frontend/e2e |
| Deployability (Compose as-is) | 30 | Frontend URL + workers/session mismatch |
| Documentation honesty | 75 | PRODUCTION_READINESS distinguishes RC vs live ops |

### Aggregate

**Overall production readiness score: 48 / 100**

- **≥70** would require fixing Critical items in §15 and validating Compose end-to-end.  
- **≥85** would additionally require IdP, tenant enforcement, migrations, load/pen tests, and removal of simulated-as-live ambiguity.

---

## 15. Critical issues

1. **CI not discoverable at git root** — nested `.github` under package.  
2. **Frontend API/WS hardcoded to `:8000`** — Compose/nginx path broken.  
3. **Demo auto-login + default shared password.**  
4. **Unauthenticated incident/assessment/report (and ops coordinate) APIs.**  
5. **In-memory sessions with uvicorn `--workers 2`.**  
6. **API-key protection documented but not applied.**  
7. **XSS via unescaped `innerHTML` on several authenticated views.**  
8. **Split ops runtime / non-durable approvals & decisions under multi-process deploy.**

---

## 16. Recommended improvements

### P0 — before any external or multi-user deploy

1. Move CI to repo-root `.github/workflows/` (or make package the git root).  
2. Change frontend `API_BASE` / WS to same-origin `/api/v1` (and `wss` behind TLS).  
3. Require session on all incident/alert/assessment/report GETs; authz on `ops/coordinate`.  
4. Run Docker with **1 worker** or shared session store (Redis) before multi-worker.  
5. Remove production auto-login; require explicit login; force strong `MERCURY_AUTH_PASSWORD`.  
6. Escape all dynamic `innerHTML` via shared `esc()` (or textContent).  
7. Wire or delete `api_key` protection; align `SECURITY.md`.

### P1 — productization

8. Enforce org/site on incident read/write by ID.  
9. Durable approvals + decision reviews (or document single-process only).  
10. Alembic (or equivalent) for Postgres.  
11. Relative URL config via env; expand CI `node --check` to all JS; add minimal Playwright smoke.  
12. Unify ops orchestrator singleton; consider consolidating event buses.  
13. Untrack/ignore `mercury.db*`; remove `tmp_*.txt`.  
14. Normalize version strings to one release identifier.

### P2 — operational maturity

15. Login rate limits; password hashing; failed-login audit.  
16. `pip-audit` / Dependabot; lockfile.  
17. Load/pen/accessibility testing; measured backup/restore drills.  
18. Real connector adapters replacing mocks.  
19. SSO/OIDC; `MERCURY_SESSION_COOKIE_SECURE=true` + TLS.  
20. Optional `/metrics` if ops requires it.

---

## Appendix A — Release artifacts present

- Milestone 1/2 specs + reports under `docs/design/`  
- Runbooks under `docs/runbooks/`  
- `docs/PRODUCTION_READINESS.md`, `FINAL_RELEASE_GUIDE.md`, `ARCHITECTURE.md`  
- Compose + Dockerfiles + nginx templates  
- Backend tests (~69) green at last gate  

## Appendix B — Explicit non-goals of this audit

- No code changes performed.  
- No penetration test or load test executed.  
- No CVE database scan beyond dependency inventory notes.  
- No claim of legal/safety certification.

---

**Audit complete.** Next human decisions: remediate Critical issues, then optionally tag RC and merge only with explicit approval.
