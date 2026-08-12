# Mercury Enterprise — Production Validation Report

**Product:** Mercury Enterprise V2.0 (package label v16)  
**Validation date:** 2026-08-10  
**Branch:** `task-16-audit-provenance`  
**Git root:** `C:\Users\14383\Downloads\Mercury_Enterprise_v16`  
**Package path:** `Mercury_Enterprise_v16/`  
**Mode:** Validation only — no functional code changes  
**APPLY_TASK ceiling:** Task 20 (final in-repo apply-task)

---

## Executive verdict

| Lens | Result |
|------|--------|
| Automated unit/API tests | **PASS** — 70/70 |
| Subsystem functional smoke (TestClient) | **PASS** for core API/auth/authz/reporting/connectors/observability/audit |
| Production packaging / deploy readiness | **FAIL** — hardcoded frontend API/WS, multi-worker in-memory sessions, CI not discoverable at git root, Docker unavailable on validator host |
| **Overall production validation** | **FAIL** (engineering RC tests pass; production deploy gates fail) |

Mercury remains a coherent **engineering Release Candidate / reference demo**. It is **not** validated for internet-exposed or safety-critical production use.

---

## Test execution summary

| Suite | Command | Result |
|-------|---------|--------|
| Backend pytest | `PYTHONPATH=backend pytest -q backend/tests` | **70 passed**, 114 warnings |
| Backend compile | `python -m compileall -q backend/app` | **PASS** |
| Frontend syntax | `node --check` on all 18 `frontend/js/*.js` | **PASS** |
| Subsystem smoke | FastAPI `TestClient` validation harness | **31 PASS / 3 FAIL** (see below) |
| Docker Compose runtime | `docker compose …` | **NOT RUN** — Docker CLI not installed on validator host |
| GitHub Actions live run | Remote CI | **NOT RUN** — workflow not at git-root `.github/` |

### Pytest modules exercised

`test_ai`, `test_alerts`, `test_api`, `test_audit`, `test_connectors`, `test_decision_engine`, `test_decisions_api`, `test_fusion`, `test_missions`, `test_observability`, `test_ops`, `test_reporting`, `test_timeline`

Warnings observed: `datetime.utcnow()` deprecation in SQLAlchemy defaults / audit / reporting (non-blocking).

---

## Subsystem pass/fail matrix

| Subsystem | Status | Evidence |
|-----------|--------|----------|
| Backend | **PASS** | 70 pytest; `compileall` clean; app imports under `TestClient` |
| Frontend | **CONDITIONAL PASS** | All JS parse via `node --check`; entry `index.html` + `app.js` present; **deploy URL/WS wiring fails packaging checks** |
| API | **PASS** | `/health` 200, `/ready` 200, `/dashboard/summary` 200, `/decisions/evaluate` 200 |
| Authentication | **PASS** | Bad password → 401; demo login → 200; `/auth/session` + `/auth/context` 200; logout clears session (reports → 401) |
| Authorization | **CONDITIONAL PASS** | Viewer denied audit (403) and decision review (403); operator review 200; **open `GET /incidents` without auth → FAIL** |
| Reporting | **PASS** | `/reports/summary` + `/reports/history` 200 for session; unauthenticated summary 401; pytest coverage |
| Connectors | **PASS** | List/health/health-history/start 200; lifecycle audited in pytest |
| Observability | **PASS** | `/platform/status` 200 (`ai=decision_engine_advisory`); `/ops/health` 200 (`advisory_only`); pytest ops/observability |
| Audit | **PASS** | Reviewer `/audit` 200; actions include login/logout/decision/connector/incident provenance |
| Packaging | **FAIL** | Compose/Dockerfiles/nginx present, but frontend hardcodes `127.0.0.1:8000`, WS hardcodes `:8000`, backend `--workers 2` with in-memory sessions; Docker not available to validate compose |
| CI | **FAIL** | Workflow exists only at `Mercury_Enterprise_v16/.github/workflows/ci.yml`; **missing** at git-root `.github/` so GitHub Actions will not discover it |

---

## Detailed subsystem results

### 1. Backend — PASS

- FastAPI application loads; routers and engines import.
- Domain coverage via pytest includes missions, alerts, timeline, fusion, AI advisory paths, decisions, connectors, ops, reporting, audit.
- No compile errors under `backend/app`.

**Residual risk (does not fail backend unit validation):** in-memory sessions/decision store are unsafe under multi-worker process models (called out under Packaging).

### 2. Frontend — CONDITIONAL PASS

| Check | Status |
|-------|--------|
| `frontend/index.html` present | PASS |
| `frontend/js/*.js` syntax (18 files) | PASS |
| `API_BASE` defined | PASS |
| Relative / proxied API base for compose | **FAIL** — `API_BASE = "http://127.0.0.1:8000/api/v1"` |
| Same-origin WebSocket via nginx | **FAIL** — `ws://${host}:8000/api/v1/ws` |
| Demo auto-login | Observed — `app.js` logs in with `mercury-demo` (demo posture; not a syntax failure) |

Frontend **code loads and parses**. Frontend **compose/nginx production topology is not validated**.

### 3. API — PASS

| Endpoint | Result |
|----------|--------|
| `GET /api/v1/health` | 200 |
| `GET /api/v1/ready` | 200, `ready=true` |
| `GET /api/v1/dashboard/summary` | 200 (includes `decisions`) |
| `POST /api/v1/decisions/evaluate` | 200, `requires_human_approval=true` |

Contracts exercised match Milestone 1–2 advisory decision model.

### 4. Authentication — PASS

| Check | Result |
|-------|--------|
| Invalid credentials | 401 |
| Valid demo credentials (`operator` / `mercury-demo`) | 200, `authenticated=true` |
| Session probe | 200 |
| Auth context (org/site) | 200 |
| Post-logout protected route | 401 on reports |

### 5. Authorization — CONDITIONAL PASS

| Check | Result |
|-------|--------|
| Viewer cannot read audit | 403 |
| Viewer cannot review decisions | 403 |
| Operator can review decisions | 200 |
| Reports require session | 401 when logged out |
| `GET /api/v1/incidents` requires auth | **FAIL — returns 200 unauthenticated** |

Incident **create/update** paths remain permission-gated; **list (and related open GETs)** remain a known production security gap from the release audit. No code change applied in this validation pass (report-only unless a regression broke tests).

### 6. Reporting — PASS

- Summary KPIs and history list succeed for authenticated operator.
- Auth boundary verified after logout.
- Pytest: scoped summary, provenance field, site exclusion.

### 7. Connectors — PASS

- Connector inventory non-empty; health + health-history + start succeed for `flight-demo` (or first listed id).
- Pytest covers lifecycle auditing.

### 8. Observability — PASS

- Platform status reports advisory AI service label.
- Ops health reports `advisory_only=true`.
- Pytest modules `test_observability` / `test_ops` pass.

**Note:** Ops health endpoints are reachable in the smoke path used by authenticated operator session; production hardening of open ops/incident reads remains an audit residual, not a pytest regression.

### 9. Audit — PASS

- Reviewer can list audit rows.
- Recent actions observed in smoke: `auth.context`, `auth.login`, `auth.logout`, connector poll/recover/start/stop, `decision.evaluate`, `decision.review`, incident create/evidence (from prior demo seed / session activity).
- Pytest covers attribution, approval trail, site scope, reviewer/admin read.

### 10. Packaging — FAIL

| Artifact | Present | Production-safe |
|----------|---------|-----------------|
| `backend/Dockerfile` | Yes | **No** — `CMD` uses `"--workers", "2"` with in-memory sessions |
| `frontend/Dockerfile` | Yes | Blocked by absolute API/WS URLs |
| `docker-compose.yml` | Yes | Not runtime-validated (no Docker CLI) |
| `frontend/nginx.conf` | Yes | Bypassed by hardcoded `:8000` client URLs |
| `.env` / compose postgres health | Present in compose | Not runtime-validated |

Validator host: **Docker not installed** (`docker` command missing) → compose config / image build / healthchecks **not executed**.

### 11. CI — FAIL

| Check | Status |
|-------|--------|
| Nested workflow `Mercury_Enterprise_v16/.github/workflows/ci.yml` | Present |
| Git-root `.github/workflows/ci.yml` | **Absent** — Actions will not run for this repo layout |
| Workflow intent | Installs deps, pytest, compileall, partial `node --check`, optional `docker compose config` |
| Workflow path assumption | `working-directory: Mercury_Enterprise_v16` implies **git-root** placement; file currently lives **inside** the package, so even local path assumptions are inconsistent |

CI content is reasonable for an RC gate **if relocated to the git root**. As checked into the current tree, CI is **not production-valid**.

---

## Smoke harness item results

Corrected packaging/CI interpretation (static review + filesystem):

| Item | Status |
|------|--------|
| `api.health` | PASS |
| `api.ready` | PASS |
| `auth.login_reject` | PASS |
| `auth.login_ok` | PASS |
| `auth.session` | PASS |
| `auth.context` | PASS |
| `authz.viewer_no_audit` | PASS |
| `api.decisions_evaluate` | PASS |
| `authz.viewer_no_decision_review` | PASS |
| `authz.operator_decision_review` | PASS |
| `reporting.summary` | PASS |
| `reporting.history` | PASS |
| `reporting.requires_auth` | PASS |
| `connectors.list` | PASS |
| `connectors.health` | PASS |
| `connectors.health_history` | PASS |
| `connectors.start` | PASS |
| `observability.platform_status` | PASS |
| `observability.ops_health` | PASS |
| `api.dashboard_summary` | PASS |
| `audit.list_reviewer` | PASS |
| `audit.has_operator_actions` | PASS |
| `security.incidents_require_auth` | **FAIL** (200 without auth) |
| `packaging.dockerfile_backend` | PASS (exists) |
| `packaging.dockerfile_frontend` | PASS (exists) |
| `packaging.compose` | PASS (exists) |
| `packaging.nginx` | PASS (exists) |
| `packaging.ci_workflow_nested` | PASS (exists) |
| `ci.github_discoverable_at_git_root` | **FAIL** |
| `frontend.api_base_defined` | PASS |
| `packaging.frontend_relative_api` | **FAIL** |
| `packaging.frontend_ws_same_origin` | **FAIL** |
| `packaging.session_safe_workers` | **FAIL** (`"--workers", "2"` in Dockerfile) |
| `frontend.entry_modules` | PASS |

---

## Failures requiring fix before production sign-off

These are **validation failures**, not pytest regressions. No functional fixes were applied in this pass (per scope: modify only if required to unblock failing validation of existing tests — existing tests all pass).

1. **Authz:** Require authentication (and appropriate permission) on `GET /api/v1/incidents` (and review other open incident GETs).
2. **Frontend packaging:** Use relative `/api/v1` (or same-origin) API base; derive WebSocket from page origin / nginx proxy without forcing `:8000`.
3. **Backend packaging:** Single worker or shared session store before multi-worker uvicorn.
4. **CI:** Place workflow at git-root `.github/workflows/` (or restructure repo so package is the git root) so Actions discovers it.
5. **Environment:** Re-run compose build/up and healthchecks on a host with Docker installed.

---

## What was not changed

- No application feature code modified.
- No authz/API/URL/Dockerfile/CI path fixes applied (would be deliberate hardening work beyond “report validation”).
- Temporary local smoke script used during validation was not retained as product code.

---

## Sign-off recommendation

| Audience | Recommendation |
|----------|----------------|
| Internal demo / engineering RC | **Accept** — tests green; core subsystems smoke-pass |
| Production / external deploy | **Reject** until packaging, CI discovery, session/worker model, and open incident reads are remediated and re-validated (including Docker compose runtime) |

**Production validation status: FAIL**
)
