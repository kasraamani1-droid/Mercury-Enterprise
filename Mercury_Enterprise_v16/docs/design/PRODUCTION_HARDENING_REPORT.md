# Mercury Enterprise V2.0 — Production Hardening Report

| Field | Value |
|-------|--------|
| **Spec** | `docs/design/PRODUCTION_HARDENING_SPEC.md` (approved) |
| **Source gate** | `docs/design/FINAL_RELEASE_GATE.md` (`NO GO`) |
| **Completed** | 2026-08-10 |
| **Merge / tag / release** | **Not performed** |

---

## Executive summary

All Critical/High blockers from the release gate were implemented across Phases 1–4 (Packaging, Security, Deployment, Validation). Backend tests: **80 passed**. Frontend `node --check`: **PASS**. Security smoke checks for anonymous sensitive routes: **PASS**.

Production readiness improves from gate **NO GO** to **CONDITIONAL GO for hardened pilot** (still not certified ops; Docker Compose runtime not re-validated on this host; deferred Medium items remain).

---

## Files changed

### Phase 1 — Packaging
- `frontend/js/config.js` — same-origin `/api/v1`; window/meta overrides
- `frontend/js/websocket.js` — same-origin WS via `resolveWsUrl()`
- `frontend/js/config.local.js.example` — local dual-process override template
- `frontend/index.html` — login overlay; optional `config.local.js` load; meta note
- `frontend/Dockerfile` — ensure empty `config.local.js` exists in image
- `frontend/css/components.css` — login overlay styles
- `START_FRONTEND.bat` — creates `config.local.js` for Windows `:3000`→`:8000`
- `backend/Dockerfile` — `--workers 1`
- `.github/workflows/ci.yml` (**git root**) — CI discoverable
- Removed nested `Mercury_Enterprise_v16/.github/workflows/ci.yml`
- `docker-compose.yml` / `docker-compose.dev.yml` — topology comments
- `README.md`, `docs/ARCHITECTURE.md`, `docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md`

### Phase 2 — Security
- `backend/app/security/authorization.py` — `incident.read`, `alerts.read`, `dashboard.read`, `platform.read`, `ops.read`, `ops.coordinate`
- `backend/app/main.py` — authz on incident GETs + tenant scope; alerts/dashboard/platform/integrations/compliance; pagination; SQL counts; startup password validation call
- `backend/app/routers/ops.py` — auth on `/ops/health` and `/ops/coordinate` + audit
- `backend/app/core/config.py` — production password rules; Secure cookie default in production
- `frontend/js/app.js` — interactive login; demo auto-login only if `__MERCURY_DEMO_AUTO_LOGIN__`
- `frontend/js/commandCenter.js`, `frontend/js/liveOps.js` — XSS escaping via `esc()`
- `docs/SECURITY.md`

### Phase 3 — Deployment
- `.env.example` — production-oriented template
- `.gitignore` — allow `.env.example`; ignore `config.local.js`
- `backend/requirements.txt` — `alembic`
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/20260810_0001_baseline.py`, `script.py.mako`
- `backend/app/database.py` — document Alembic vs `create_all`
- Incident list `limit`/`offset` caps; dashboard `func.count()`

### Phase 4 — Validation / tests
- `backend/tests/test_api.py`, `test_audit.py`, `test_observability.py`, `test_ops.py` — auth expectations
- `backend/tests/test_hardening_security.py` — **new** security verification suite

---

## Security fixes

| Gate ID | Fix |
|---------|-----|
| C5 | Incident list/detail/assessment/report require `incident.read`; org/site scoped; cross-tenant → 404 |
| C6 | `POST /ops/coordinate` requires `ops.coordinate`; audited |
| H1 | Alerts, dashboard, platform, integrations, compliance, ops health require auth + permissions |
| C7 | Removed default demo auto-login; login overlay; opt-in `__MERCURY_DEMO_AUTO_LOGIN__` only |
| C8 | Production refuses missing/short/`mercury-demo` password at startup |
| H4 | `MERCURY_SESSION_COOKIE_SECURE` defaults **true** when `MERCURY_ENV=production` |
| H5 | Escaped dynamic HTML in `commandCenter.js` / `liveOps.js` |

Public probes unchanged: `/health`, `/ready`.

---

## Packaging fixes

| Gate ID | Fix |
|---------|-----|
| C1 | Default `API_BASE` = `/api/v1` with window/meta override |
| C2 | WS derived from page origin (`ws`/`wss` + host + `/api/v1/ws`) |
| C3 | Docs/compose clarify NGINX same-origin path; dev compose labeled escape hatch |
| C4 | Dockerfile `--workers 1` (matches in-memory sessions) |
| H2 | CI workflow at git-root `.github/workflows/ci.yml` |

---

## Deployment fixes

| Gate ID | Fix |
|---------|-----|
| H7 | `.env.example` checked in; `.gitignore` allows it |
| H3 | Alembic baseline migration + runbook steps; SQLite still uses `create_all` |
| H6 | Incident list capped (`limit` max 500, default 100); dashboard uses SQL count |

---

## Validation results

### Automated tests
| Suite | Result |
|-------|--------|
| `pytest -q backend/tests` | **80 passed** |
| `python -m compileall backend/app` | **PASS** |
| `node --check` all `frontend/js/*.js` | **PASS** |

### Security verification (spec §4.2)
| Check | Result |
|-------|--------|
| Anonymous incident GETs | **401** |
| Anonymous ops coordinate | **401** |
| Anonymous alerts/dashboard/platform/ops health | **401** |
| `/health` `/ready` public | **200** |
| No silent demo auto-login in default path | **PASS** (requires UI / flag) |
| Production password guard | **PASS** (unit) |
| Viewer cannot ops.coordinate | **403** |
| Viewer can incident.read | **200** |
| XSS sinks (commandCenter/liveOps) | Escaped |

### Packaging checks
| Check | Result |
|-------|--------|
| Relative API default | **PASS** |
| WS no forced `:8000` | **PASS** |
| Dockerfile workers=1 | **PASS** |
| Git-root CI workflow | **PASS** |
| Nested package CI removed | **PASS** |
| Compose runtime on this host | **NOT RUN** (Docker CLI absent) |

---

## Test results (detail)

- Prior baseline: 70 tests  
- After hardening: **80 tests** (added security/ops auth coverage + pagination/guard checks)  
- Warnings: `datetime.utcnow()` deprecation (pre-existing; non-blocking)

---

## Remaining known issues

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| M1 | In-memory decisions/approvals/missions | Medium | Option A by design; HA needs follow-on |
| M2 | `MERCURY_API_KEY` unused | Medium | Documented reserved; session RBAC primary |
| M3 | CORS `allow_headers=["*"]` | Medium | Optional tighten |
| M4 | Simulated feeds / non-certified AI | Medium | Product scope — not a code defect |
| M5 | Compose not runtime-validated here | Medium | Re-run on Docker host before pilot |
| L1 | `utcnow` warnings | Low | Cleanup backlog |
| L2 | Version label drift in some bats | Low | Cosmetic |
| — | Shared session store for multi-worker | Medium | Deferred; workers locked to 1 |
| — | OIDC/SSO/MFA | High (future) | Out of hardening scope |
| — | Residual XSS in other modules | Low–Med | Spec called out commandCenter/liveOps; broader audit optional |

---

## Production readiness assessment

| Audience | Assessment |
|----------|------------|
| Engineering RC / localhost demo | **GO** (with interactive login + local `config.local.js`) |
| Compose/NGINX pilot behind TLS + strong secrets | **CONDITIONAL GO** — blockers C1–C8/H1–H7 addressed; validate Compose on Docker host; set `.env` from `.env.example` |
| Certified / internet-exposed / safety-critical ops | **NO GO** — simulated feeds, no SSO, no HA session store, accreditation unfinished |

**Hardening status vs prior gate:** production blockers from `FINAL_RELEASE_GATE.md` are **remediated in code/config**. Re-run a formal gate after Compose smoke on a Docker-equipped host before tagging.

---

## Explicit non-actions

- **No merge**
- **No tag**
- **No release**

Stopped after this report.
