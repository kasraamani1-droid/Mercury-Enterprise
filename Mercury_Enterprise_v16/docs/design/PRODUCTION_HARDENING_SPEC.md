# Mercury Enterprise V2.0 — Production Hardening Specification

| Field | Value |
|-------|--------|
| **Document** | Engineering specification only |
| **Source of truth** | `docs/design/FINAL_RELEASE_GATE.md` (`RELEASE STATUS: NO GO`) |
| **Goal** | Clear production blockers so a future gate can reach **GO** |
| **Architecture constraints** | Additive changes only; vanilla JS frontend; FastAPI backend; no SPA framework |
| **Out of scope for this spec** | New product features; OIDC/SSO implementation; certified hardware adapters; autonomous response |
| **Implementation** | **Not started** — do not modify code until this spec is approved |

---

## Principles

1. Treat every **Critical** and **High** gate ID as mandatory unless an explicit written waiver is approved.
2. Prefer additive API guards and configuration over rewrites.
3. Preserve human-control / advisory decision invariants.
4. Local Windows SQLite demo may remain supported via **explicit** opt-in env flags — production defaults must be safe.
5. After all phases: re-run `FINAL_RELEASE_GATE` criteria and update validation docs.

---

## Phase overview

| Phase | Theme | Gate IDs |
|-------|--------|----------|
| **1** | Packaging | C1, C2, C3, C4, H2 |
| **2** | Security | C5, C6, C7, C8, H1, H4, H5 |
| **3** | Deployment | H3, H6, H7 (+ config/secrets from C8/H4) |
| **4** | Validation | All — retest, security verify, checklist |

Medium/Low (M1–M5, L1–L3) are **deferred** unless noted as follow-ups inside a phase; they are not primary blockers for an initial production-hardening cut except where called out.

---

# Phase 1 — Packaging

**Objective:** Remove localhost assumptions; make API/WS endpoints environment-correct; make CI discoverable; make session model match process model.

---

## Blocker C1 — Hardcoded API base (`127.0.0.1:8000`)

### 1. Root cause
`frontend/js/config.js` sets `API_BASE` to an absolute local URL for dual-process Windows demo. Clients never use NGINX `/api` proxy.

### 2. Type
**Code** (frontend config) + **configuration** (optional override) + **deployment** (Compose/NGINX topology assumes relative `/api`).

### 3. Production impact
Browser calls host loopback `:8000` instead of same-origin proxy → failed API calls in Compose (backend not published) or unintended direct backend exposure if port is published.

### 4. Severity
**Critical**

### 5. Files to modify
- `frontend/js/config.js`
- Call sites importing `API_BASE` (verify only; expect no logic change): `frontend/js/api.js` and any direct imports
- Optionally `frontend/js/app.js` if bootstrap must read runtime override
- Docs: `README.md`, `docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md`, `docs/ARCHITECTURE.md` (document resolution order)

### 6. Exact implementation
1. Change default `API_BASE` to same-origin relative path: `"/api/v1"`.
2. Allow optional override via (in order):
   - `window.__MERCURY_API_BASE__` (injected by deploy), or
   - `<meta name="mercury-api-base" content="...">`, or
   - query/build-time only if already used — prefer runtime meta/window for no bundler.
3. Keep Windows local demo working by documenting that local static server must either:
   - proxy `/api` to backend, **or**
   - set override to `http://127.0.0.1:8000/api/v1` via a small `frontend/js/config.local.js` that is **gitignored**, **or**
   - use Compose/dev compose that publishes API consistently.
4. Do **not** leave production default as `127.0.0.1:8000`.

### 7. Rollback
Revert `config.js` to previous absolute URL; redeploy frontend image/static assets. No DB change.

### 8. Testing
- Unit/manual: with override unset, `fetch` paths resolve under `http://localhost:3000/api/v1/...` through NGINX.
- Compose: UI login and dashboard succeed without host `:8000` published.
- Local override path still reaches API when explicitly configured.
- `node --check frontend/js/config.js`

---

## Blocker C2 — WebSocket hardcodes `:8000`

### 1. Root cause
`frontend/js/websocket.js` builds `ws://${host}:8000/api/v1/ws`, ignoring page origin and NGINX upgrade proxy.

### 2. Type
**Code** (frontend) + **deployment** (NGINX already proxies WS).

### 3. Production impact
Live updates fail in Compose; operators see disconnect/retry loops; may attempt forbidden direct backend ports.

### 4. Severity
**Critical**

### 5. Files to modify
- `frontend/js/websocket.js`
- Optionally `frontend/js/config.js` (export `WS_URL` helper beside `API_BASE`)
- `frontend/nginx.conf` (verify only — already has `/api/v1/ws`)
- `deploy/nginx-production.conf` if present (verify parity)

### 6. Exact implementation
1. Derive socket URL from `window.location`:
   - `const proto = location.protocol === "https:" ? "wss:" : "ws:";`
   - `return `${proto}//${location.host}/api/v1/ws`;`
2. Optional override `window.__MERCURY_WS_URL__` for exceptional topologies.
3. Remove hardcoded `:8000`.

### 7. Rollback
Restore previous `socketUrl()` implementation; redeploy frontend.

### 8. Testing
- Compose: WS connects via `:3000` → NGINX → backend; heartbeat received.
- Login-required WS still closes without session (existing behavior).
- `node --check frontend/js/websocket.js`

---

## Blocker C3 — Compose / NGINX vs client mismatch

### 1. Root cause
Topology is correct server-side (frontend publishes `:3000`, backend `expose` only, NGINX proxies `/api`), but clients bypass it (C1/C2). Docs still describe “open localhost:3000” without stating same-origin API requirement.

### 2. Type
**Deployment** + **documentation** (code fixed primarily via C1/C2).

### 3. Production impact
“Works on my machine” local dual-port ≠ works in reference production Compose; false confidence in packaging.

### 4. Severity
**Critical** (as a system gap; remediated with C1/C2 + doc clarity)

### 5. Files to modify
- `docker-compose.yml` (comments / healthcheck notes only unless a deliberate `profiles` for publishing `:8000` in **dev**)
- `docker-compose.dev.yml` (keep or clarify published `:8000` as **dev-only**)
- `README.md`, `docs/RELEASE_NOTES_v2.0.md` deployment section, `docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md`, `docs/ARCHITECTURE.md`
- Do **not** publish backend `:8000` on production Compose by default

### 6. Exact implementation
1. Document canonical production path: Browser → `:3000` → NGINX `/api` + `/api/v1/ws` → `backend:8000`.
2. After C1/C2, verify compose file needs **no** host port on backend for UI operation.
3. Label `docker-compose.dev.yml` as developer escape hatch only.
4. Add smoke steps: `curl` via frontend host `/api/v1/ready` (through proxy), not only direct backend.

### 7. Rollback
Revert doc/compose comment changes; if any accidental port publish was added, remove it.

### 8. Testing
- `docker compose config` validates.
- From host: `http://localhost:3000/api/v1/ready` returns ready (via NGINX).
- Direct `localhost:8000` fails when not published (expected in prod compose).

---

## Blocker C4 — In-memory sessions + `--workers 2`

### 1. Root cause
Sessions live in process dict `_sessions` in `main.py`. Dockerfile runs uvicorn with two workers → session created on worker A often invalid on worker B.

### 2. Type
**Code** (session storage design) and/or **configuration/deployment** (worker count).

### 3. Production impact
Intermittent 401 after login, flaky authz, broken operator workflows under Compose image defaults.

### 4. Severity
**Critical**

### 5. Files to modify
- `backend/Dockerfile` (**required minimum**)
- Optionally later: `backend/app/main.py` session helpers (only if implementing shared store — **out of Phase 1 minimum**)
- `docs/ARCHITECTURE.md`, `docs/SECURITY.md` (document single-worker constraint until shared sessions exist)

### 6. Exact implementation (Phase 1 minimum — choose Option A)
**Option A (required for this phase):** Change Dockerfile CMD to single worker:
```text
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```
or omit `--workers` (uvicorn default 1).

**Option B (deferred):** Redis/DB-backed session store — separate follow-on spec; do not combine with Phase 1 unless explicitly approved.

Also align any compose command overrides if present.

### 7. Rollback
Restore `--workers 2` only if shared sessions already deployed; otherwise rollback is unsafe. Prefer keep workers=1.

### 8. Testing
- Compose: repeated login + authenticated GETs across many requests (no flapping 401).
- Existing auth pytest suite still passes.
- Document that horizontal scale requires Option B first.

---

## Blocker H2 — CI not at git root

### 1. Root cause
Workflow file lives at `Mercury_Enterprise_v16/.github/workflows/ci.yml`. GitHub Actions only loads `.github` from **repository root** (`C:\Users\...\Mercury_Enterprise_v16`). Nested workflow is invisible. YAML `working-directory: Mercury_Enterprise_v16` assumes root placement.

### 2. Type
**Deployment/CI layout** (file move) + light **documentation**.

### 3. Production impact
No automated gate on push/PR; regressions can merge unnoticed.

### 4. Severity
**High** (gate-listed production blocker)

### 5. Files to modify
- Create: `<git-root>/.github/workflows/ci.yml`
- Remove or leave stub notice in nested path (prefer **move**: delete nested duplicate to avoid drift)
- Nested path today: `Mercury_Enterprise_v16/.github/workflows/ci.yml`

### 6. Exact implementation
1. Copy workflow to git-root `.github/workflows/ci.yml`.
2. Keep:
   - `defaults.run.working-directory: Mercury_Enterprise_v16`
   - pytest, compileall, `node --check` set, compose config best-effort
3. Delete nested `.github` workflow to prevent dual sources of truth.
4. Ensure paths in steps match package layout.

### 7. Rollback
Move file back to nested location (CI will stop again — acceptable only for emergency).

### 8. Testing
- Confirm git-root path exists in a dry-run file tree review.
- On next push (when allowed): Actions run appears; pytest job green.
- Locally still run the same commands manually in Phase 4.

---

# Phase 2 — Security

**Objective:** Require authentication where appropriate; remove demo login; secure ops; verify authorization and browser hardening.

---

## Blocker C5 — Unauthenticated incident reads + missing tenant filter

### 1. Root cause
Legacy demo openness: `GET /incidents`, `GET /incidents/{id}`, assessment, and report lack `require_session` / permissions. List returns all rows without org/site filter despite tenancy columns.

### 2. Type
**Code** (API authz) + tests + minor **documentation** (breaking change for anonymous clients).

### 3. Production impact
Full incident confidentiality breach; cross-tenant IDOR; fails any multi-site deploy.

### 4. Severity
**Critical**

### 5. Files to modify
- `backend/app/main.py` (route dependencies + query filters)
- `backend/app/security/authorization.py` (add `incident.read` if missing; grant to Operator/Reviewer/Viewer/Admin as appropriate)
- `backend/tests/test_api.py`, `test_audit.py`, and any incident helpers
- Frontend: `frontend/js/incidents.js` / `app.js` — ensure calls run **after** authenticated session (no anonymous fetch reliance)

### 6. Exact implementation
1. Add permission `incident.read` (or reuse a documented existing read permission if one already covers this — prefer explicit `incident.read`).
2. Apply `Depends(require_permissions("incident.read"))` (or `require_session` + permission) to:
   - `GET /incidents`
   - `GET /incidents/{id}`
   - `GET /incidents/{id}/assessment`
   - `GET /incidents/{id}/report`
3. Scope list/detail queries to `session["organization_id"]` / `session["site_id"]` (Administrator may be all-sites only if already established elsewhere — match reports/audit patterns).
4. Return 401 unauthenticated, 403 unauthorized, 404 for cross-tenant IDs (avoid existence leak where practical).
5. Update OpenAPI implicitly via FastAPI dependencies.

### 7. Rollback
Revert route dependencies and filters; redeploy backend. Note: temporary re-exposure — only for emergency with network isolation.

### 8. Testing
- Unauthenticated GET incidents → 401/403.
- Viewer with `incident.read` sees only scoped rows.
- Cross-site ID → 404/403.
- Existing create/update permission tests still pass.
- Frontend incident list works after real login.

---

## Blocker C6 — Unauthenticated `POST /ops/coordinate`

### 1. Root cause
Ops router exposes orchestration write with no `Depends` auth. Classified in gate as **bug/security defect**.

### 2. Type
**Code**

### 3. Production impact
Anyone who can reach the API can inject orchestration events — integrity and potential operational confusion (even if advisory).

### 4. Severity
**Critical**

### 5. Files to modify
- `backend/app/routers/ops.py`
- `backend/app/security/authorization.py` (add `ops.coordinate` or reuse admin/operator permission)
- `backend/tests/test_ops.py`

### 6. Exact implementation
1. Add permission e.g. `ops.coordinate` to Operator + Administrator (not Viewer).
2. `coordinate` endpoint: `dependencies=[Depends(require_permissions("ops.coordinate"))]` (import same helpers used by connectors/main).
3. Optionally audit `ops.coordinate` on success.
4. Keep response advisory/`automatic_execution` false invariants unchanged.

### 7. Rollback
Remove dependency (not recommended). Prefer keep auth and disable route via feature flag if needed.

### 8. Testing
- Unauthenticated POST → 401/403.
- Viewer → 403.
- Operator → 200 and existing payload shape.
- Extend `test_ops.py` accordingly.

---

## Blocker H1 — Open alerts / dashboard / platform / integrations / compliance / ops health

### 1. Root cause
Same demo-era open-read pattern as C5; diagnostics and summary endpoints left public.

### 2. Type
**Code** + **documentation** (what remains public: `/health`, `/ready` only)

### 3. Production impact
Information disclosure (alerts, integrations, compliance posture, ops internals); dashboard data without login.

### 4. Severity
**High**

### 5. Files to modify
- `backend/app/main.py` (`/alerts`, `/dashboard/summary`, `/platform/status`, `/integrations`, `/compliance`)
- `backend/app/routers/ops.py` (`GET /health`)
- `backend/app/security/authorization.py` (permissions such as `alerts.read`, `dashboard.read`, `ops.read`, or map to existing roles)
- Tests: `test_api.py`, `test_observability.py`, `test_ops.py`
- Frontend loaders must tolerate 401 and prompt login

### 6. Exact implementation
1. **Keep public:** `GET /health`, `GET /ready` only (probes).
2. Require session + appropriate read permission for:
   - `GET /alerts`
   - `GET /dashboard/summary`
   - `GET /platform/status`
   - `GET /integrations`
   - `GET /compliance`
   - `GET /ops/health`
3. Align role grants: Viewer may read dashboard/alerts if product requires; ops health may be Operator+Admin only — **choose least privilege**; document in SECURITY.md.
4. Do not break probe-based Compose healthchecks (they use `/ready` on backend network — OK).

### 7. Rollback
Revert dependencies per endpoint.

### 8. Testing
- Unauthenticated calls → 401/403.
- Authenticated role matrix tests.
- Compose backend healthcheck still green.
- UI pages load after login only.

---

## Blocker C7 — Frontend demo auto-login

### 1. Root cause
`ensureSession()` in `app.js` calls `login({ operator: "operator", password: "mercury-demo" })` when unauthenticated — intentional demo posture.

### 2. Type
**Code** (frontend) + **documentation**

### 3. Production impact
Any exposed UI silently authenticates with known credentials → full auth bypass from attacker’s perspective.

### 4. Severity
**Critical**

### 5. Files to modify
- `frontend/js/app.js` (`ensureSession`)
- Possibly login UI handlers already present — wire mandatory interactive login
- `docs/SECURITY.md`, `docs/runbooks/OPERATOR.md`

### 6. Exact implementation
1. Remove hardcoded demo login from production path.
2. `ensureSession()`: if not authenticated, show login UI / redirect to login controls; **do not** POST credentials automatically.
3. Optional **dev-only** auto-login behind explicit flag, e.g. `window.__MERCURY_DEMO_AUTO_LOGIN__ === true` or `localStorage` key, default **false**. Never enable in Compose production docs.
4. Ensure Command workspace waits for authenticated session before data fetches (coordinates with C5/H1).

### 7. Rollback
Restore auto-login only for isolated demos with network controls.

### 8. Testing
- Cold load without cookie → login prompt, no network login with `mercury-demo` unless flag set.
- Manual login still works.
- `node --check frontend/js/app.js`

---

## Blocker C8 — Default password `mercury-demo`

### 1. Root cause
`Settings.auth_password` defaults to `"mercury-demo"` when `MERCURY_AUTH_PASSWORD` unset — convenient for demos, unsafe for any shared deploy.

### 2. Type
**Code** (config defaults) + **configuration** (env required in prod) + **documentation**

### 3. Production impact
Predictable credential if env forgotten; pairs catastrophically with C7.

### 4. Severity
**Critical**

### 5. Files to modify
- `backend/app/core/config.py`
- `backend/app/main.py` (startup guard optional)
- `.env.example` (Phase 3 H7)
- `docs/SECURITY.md`, runbooks, `README.md`
- Tests that hardcode `mercury-demo` — keep password **in tests only** via env monkeypatch/fixture

### 6. Exact implementation
1. In `production` / non-development environments (`MERCURY_ENV` not `development`): **require** `MERCURY_AUTH_PASSWORD` to be set and sufficiently long; refuse startup if missing or equal to `mercury-demo`.
2. Development default may remain `mercury-demo` **only** when `MERCURY_ENV=development` (document clearly).
3. Pytest sets env explicitly so CI/dev tests remain stable.
4. Compose production `.env` must set strong password (Phase 3).

### 7. Rollback
Relax startup guard (increases risk) — avoid in prod.

### 8. Testing
- `MERCURY_ENV=production` without password → app fails fast.
- Development + tests → still pass with fixture password.
- Login with configured password succeeds.

---

## Blocker H4 — Cookie `Secure` default false

### 1. Root cause
`MERCURY_SESSION_COOKIE_SECURE` defaults to `False` for easy HTTP local demo.

### 2. Type
**Configuration** (+ small **code** defaulting by env) + **documentation**

### 3. Production impact
Session cookie eligible for transmission over cleartext HTTP → session theft on network path.

### 4. Severity
**High**

### 5. Files to modify
- `backend/app/core/config.py`
- Login cookie set site in `backend/app/main.py` (verify uses settings flag)
- `.env.example`, SECURITY/runbooks

### 6. Exact implementation
1. If `MERCURY_ENV=production` (or TLS termination indicated): default `session_cookie_secure=True`.
2. Development may keep false for HTTP localhost.
3. Document that TLS must terminate at NGINX/load balancer when Secure is true.
4. Do not force Secure=true on pure HTTP local or cookies become unsettable — env-aware defaulting required.

### 7. Rollback
Set env `MERCURY_SESSION_COOKIE_SECURE=false` for emergency HTTP-only lab.

### 8. Testing
- Production settings: Set-Cookie contains `Secure`.
- Development HTTP login still works.
- Auth tests pass with overrides.

---

## Blocker H5 — Residual XSS (`innerHTML`)

### 1. Root cause
Incomplete escape pass; some modules insert untrusted/dynamic strings via `innerHTML` without `esc()`.

### 2. Type
**Code** (frontend)

### 3. Production impact
Stored/reflected XSS if attacker-controlled titles/text reach DOM (esp. once incidents are authenticated but multi-operator).

### 4. Severity
**High**

### 5. Files to modify (minimum from gate)
- `frontend/js/commandCenter.js`
- `frontend/js/liveOps.js`
- Audit remaining `innerHTML` in `frontend/js/*.js` and fix unsafe sinks (reuse `esc` from `utils.js`)
- Prefer textContent/DOM APIs where simple

### 6. Exact implementation
1. Wrap dynamic strings with existing `esc()`.
2. For static simulation labels, escaping still preferred for consistency.
3. No new framework; keep vanilla JS.

### 7. Rollback
Revert individual file edits.

### 8. Testing
- `node --check` on touched files.
- Manual: notification title containing `<script>` or `<img onerror>` renders as text.
- No regression in Command/live panels layout.

---

# Phase 3 — Deployment

**Objective:** Production configuration, secrets, environment variables, DB lifecycle hygiene, API list bounds.

---

## Blocker H7 — Missing `.env.example`

### 1. Root cause
Compose references `env_file: .env` but no checked-in template; operators guess variable names.

### 2. Type
**Documentation** + **configuration template** (not secrets)

### 3. Production impact
Misconfigured deploys; accidental demo defaults in “prod”; slower/error-prone rollout.

### 4. Severity
**High**

### 5. Files to modify
- Create `Mercury_Enterprise_v16/.env.example`
- `README.md`, `docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md`
- Ensure `.gitignore` ignores `.env` (verify)

### 6. Exact implementation
Provide template keys (placeholders only):
- `DATABASE_URL=`
- `MERCURY_ENV=production`
- `MERCURY_AUTH_PASSWORD=`
- `MERCURY_AUTH_OPERATOR=`
- `MERCURY_CORS_ORIGINS=`
- `MERCURY_SESSION_COOKIE_SECURE=true`
- `MERCURY_SESSION_SAMESITE=lax`
- `MERCURY_SEED_DEMO=false`
- `MERCURY_LOG_JSON=true`
- `MERCURY_AUDIT_RETENTION_DAYS=365`
- Comments pointing to SECURITY.md

### 7. Rollback
Delete template (not recommended).

### 8. Testing
- Copy to `.env`, fill values, `docker compose config` succeeds.
- No real secrets committed.

---

## Blocker H3 — No Alembic / Postgres ALTER gap

### 1. Root cause
`ensure_schema()` uses `create_all`; column ALTERs run only for SQLite. Postgres upgrades that need additive columns on existing DBs are unsupported.

### 2. Type
**Code** (migrations) + **deployment** process + **documentation**

### 3. Production impact
Schema drift/failure on upgrade; unsafe hotfixes via manual SQL; blocks reliable prod DB lifecycle.

### 4. Severity
**High** (waivable only for disposable DBs)

### 5. Files to modify
- Add migration tooling under `backend/` (e.g. Alembic `alembic.ini`, `backend/alembic/versions/…`)
- `backend/app/database.py` (call migrations on startup **or** document explicit migrate step in deploy — prefer explicit deploy step over implicit surprise)
- `backend/requirements.txt` (add `alembic` if chosen)
- Runbooks: deploy/upgrade/rollback
- CI: optional `alembic check` / upgrade on empty Postgres service

### 6. Exact implementation
1. Baseline migration matching current models (`incidents`, `timeline_events`, `evidence`, `audit_events` + indexes/columns).
2. Deploy procedure: `alembic upgrade head` before/alongside backend start.
3. Keep `create_all` for empty SQLite dev **or** unify on Alembic for both — pick one story; document.
4. Remove reliance on SQLite-only ALTER for production path.

### 7. Rollback
`alembic downgrade -1` when downgrade path exists; else restore DB backup per DR runbook. App code rollback without DB downgrade if migration was additive-compatible.

### 8. Testing
- Fresh Postgres: migrate → app ready.
- Second migrate: no-op.
- SQLite dev path still works per chosen strategy.
- pytest against SQLite (CI) remains green.

---

## Blocker H6 — Unbounded incident list / dashboard full scan

### 1. Root cause
`list_incidents` and dashboard summary load all incidents without `limit`/aggregation query.

### 2. Type
**Code** (API performance hygiene)

### 3. Production impact
Latency and memory growth with dataset size; potential DoS against API/DB.

### 4. Severity
**High** (conditional blocker at scale; include in hardening cut)

### 5. Files to modify
- `backend/app/main.py` (`list_incidents`, `dashboard_summary`)
- Schemas if pagination metadata added
- `backend/tests/test_api.py`
- Frontend list rendering if pagination params required

### 6. Exact implementation
1. `GET /incidents?limit=&offset=` (or cursor) with server-side max cap (e.g. 100 default, 500 max).
2. Dashboard: use SQL `count()` / filtered counts instead of loading all rows into Python.
3. Preserve newest-first ordering.

### 7. Rollback
Revert to unpaged list (only for tiny demos).

### 8. Testing
- Default list length ≤ cap.
- Dashboard counts match DB for fixtures.
- Performance sanity with seeded N rows (optional script).

---

## Phase 3 configuration bundle (cross-cutting)

| Item | Action |
|------|--------|
| Secrets | Only via env/secret manager; never commit `.env` |
| `MERCURY_CORS_ORIGINS` | Exact production UI origins |
| `MERCURY_SEED_DEMO` | `false` in production |
| `MERCURY_LOG_JSON` | `true` behind collectors |
| TLS | Terminate at edge; Secure cookies on |
| Workers | Remain 1 until shared sessions (Phase 1 C4) |
| M2 API key | Leave **unenforced** or implement properly in a later spec — do **not** document as active control (M2) |

### Rollback (Phase 3)
Restore previous `.env` from secret backup; redeploy prior images; DB restore only if migration corrupted data.

### Testing (Phase 3)
Compose up with production-like `.env`; `/ready`; login; no demo seed if disabled; cookie flags verified.

---

# Phase 4 — Validation

**Objective:** Prove blockers are cleared; regenerate gate evidence; decide GO/NO GO.

---

## 4.1 Rerun all automated tests

### Implementation
From package dir with `PYTHONPATH=backend`:
1. `pytest -q backend/tests` — expect all pass (update counts in report)
2. `python -m compileall -q backend/app`
3. `node --check` on all `frontend/js/*.js`
4. CI workflow at git root equivalent commands

### Rollback
N/A (validation only)

### Testing
Treat failures as phase regressions; do not declare GO.

---

## 4.2 Security verification

### Exact checks
| Check | Pass criteria |
|-------|----------------|
| Anonymous incident GETs | 401/403 |
| Anonymous ops coordinate | 401/403 |
| Anonymous alerts/dashboard/platform/ops health | 401/403 |
| `/health` `/ready` | 200 without auth |
| No auto-login | No silent `mercury-demo` login in network log |
| Production env without password | Startup fail |
| Secure cookie in prod settings | Present |
| XSS sample strings | Escaped in UI |
| RBAC matrix | Viewer cannot coordinate/review as designed; can only use granted reads |

### Files to update (docs only after evidence)
- `docs/design/PRODUCTION_VALIDATION_REPORT.md` (regenerate)
- `docs/design/FINAL_RELEASE_GATE.md` (new gate run)
- `docs/SECURITY.md` (align claims with enforcement)

---

## 4.3 Packaging / deployment verification

| Check | Pass criteria |
|-------|----------------|
| Compose UI | Login + API + WS via `:3000` only |
| Backend port | Not required on host for UI |
| Workers | 1 (or shared sessions proven) |
| CI path | Git-root `.github/workflows/ci.yml` exists |
| `.env.example` | Present; compose works from copy |

---

## 4.4 Production checklist (gate exit)

- [ ] Phase 1 C1–C4, H2 closed
- [ ] Phase 2 C5–C8, H1, H4, H5 closed
- [ ] Phase 3 H3, H6, H7 closed (or H3 formally waived with disposable DB acknowledgment)
- [ ] All tests green
- [ ] Security verification table green
- [ ] Compose smoke on Docker-equipped host
- [ ] Runbooks updated for new auth and env requirements
- [ ] Explicit statement: simulated feeds still non-certified (M4 remains scope limit — not a code bug)

**Only then** recommend updating release gate to:

```text
RELEASE STATUS: GO
```

(for production **pilot** under TLS, strong secrets, and remaining scope limits).

---

## Deferred (not in Phases 1–3 mandatory set)

| ID | Item | Disposition |
|----|------|-------------|
| M1 | Shared durable decisions/approvals/missions | Follow-on HA spec |
| M2 | Enforce or remove API-key claims | Follow-on; docs honesty already partially done |
| M3 | Tighten CORS headers list | Quick win optional in Phase 2/3 |
| M4 | Simulated feeds / certification | Product/process — out of hardening code scope |
| M5 | Docker-less hosts | Environmental — validate on Docker host in Phase 4 |
| L1–L3 | utcnow warnings, label drift, partial XSS history | Cleanup backlog |

---

## Suggested implementation order (within approval)

1. Phase 1 (C1→C2→C3 docs→C4→H2) — restore deployability  
2. Phase 2 (C6→C5→H1→C7→C8→H4→H5) — close exposure  
3. Phase 3 (H7→H3→H6 + env bundle) — operable production config  
4. Phase 4 — evidence for GO  

---

## Approval gate

This document is the **only** deliverable of this step.

| Action | Status |
|--------|--------|
| Spec written | **Yes** — `docs/design/PRODUCTION_HARDENING_SPEC.md` |
| Code modified | **No** |
| Merge / tag | **No** |

**Stop. Await approval before implementing any phase.**
)
