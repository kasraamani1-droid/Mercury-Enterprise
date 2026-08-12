# Mercury Enterprise V2.0 RC — Final Release Gate

| Field | Value |
|-------|--------|
| **Product** | Mercury Enterprise V2.0 RC (package `16.0.0`) |
| **Gate date** | 2026-08-10 |
| **Branch** | `task-16-audit-provenance` |
| **Scope** | Read-only repository review for **production** readiness |
| **Code changes** | **None** (blockers documented; fixes proposed, not applied) |
| **Merge / tag** | **Not performed** |

**Companion evidence:** `docs/design/PRODUCTION_VALIDATION_REPORT.md`, `FINAL_RELEASE_AUDIT.md`, `RELEASE_NOTES_v2.0.md`, pytest **70/70**.

---

## 1. Overall release status

| Audience | Status |
|----------|--------|
| Engineering RC / controlled internal demo | **CONDITIONAL GO** (tests green; features through Task 20 present) |
| Internet-exposed or live operational production | **NO GO** |

Mercury V2.0 RC is a coherent **reference / demo platform**, not a production-hardened deployment. Automated tests and Milestone 1–2 feature delivery succeed; packaging topology, authorization completeness, session durability, and demo identity posture **fail production gates**.

```text
RELEASE STATUS: NO GO
```

---

## 2. Remaining issues

### Critical

| ID | Issue | Evidence |
|----|--------|----------|
| C1 | Frontend hardcodes API to `http://127.0.0.1:8000` | `frontend/js/config.js` |
| C2 | WebSocket hardcodes `ws://{host}:8000` | `frontend/js/websocket.js` |
| C3 | Compose does not publish backend `:8000`; NGINX expects same-origin `/api` — clients bypass proxy | `docker-compose.yml`, `frontend/nginx.conf` |
| C4 | In-memory sessions + uvicorn `--workers 2` | `main.py` `_sessions`; `backend/Dockerfile` |
| C5 | Unauthenticated incident reads (list/detail/assessment/report) + no org/site filter on list | `main.py` |
| C6 | Unauthenticated `POST /api/v1/ops/coordinate` (orchestration write) | `routers/ops.py` |
| C7 | Frontend demo auto-login with shared password | `app.js` `ensureSession()` → `mercury-demo` |
| C8 | Default `MERCURY_AUTH_PASSWORD=mercury-demo` | `core/config.py` |

### High

| ID | Issue | Evidence |
|----|--------|----------|
| H1 | Unauthenticated `GET /alerts`, open-ish dashboard/platform/integrations/compliance/ops health | `main.py`, `ops.py` |
| H2 | CI workflow not at git-root `.github/` — Actions will not discover it | nested `Mercury_Enterprise_v16/.github/workflows/ci.yml` |
| H3 | No Alembic; Postgres path is `create_all` only; additive ALTERs are SQLite-only | `database.py` |
| H4 | Cookie `Secure` default false | `MERCURY_SESSION_COOKIE_SECURE` |
| H5 | Residual XSS via unsanitized `innerHTML` | e.g. `commandCenter.js`, `liveOps.js` |
| H6 | Unbounded `GET /incidents` / dashboard full-table scan | `main.py` |
| H7 | Missing `.env.example` while Compose expects `.env` | packaging tree |

### Medium

| ID | Issue | Evidence |
|----|--------|----------|
| M1 | Decision/approval/mission/connector runtime state mostly process-local | decision store, `_approvals`, mission manager |
| M2 | `MERCURY_API_KEY` reserved but not enforced on routes | config + SECURITY.md |
| M3 | CORS `allow_headers=["*"]`; credentials enabled | `main.py` |
| M4 | Simulated feeds / non-certified AI — unsuitable for live safety decisions | product scope |
| M5 | Compose runtime not validated on hosts without Docker | validation report |

### Low

| ID | Issue | Evidence |
|----|--------|----------|
| L1 | `datetime.utcnow()` deprecation warnings in tests | pytest noise |
| L2 | Version/label drift (v10/v15/v16/V2.0) in legacy docs/scripts | README vs IMPLEMENTATION_STATUS |
| L3 | Partial XSS cleanup already done in enterprise/timeline paths | cleanup report |

---

## 3. Packaging gaps (explained)

**What “packaging” means here:** Docker/Compose/NGINX/CI/client URL wiring so a browser hitting `:3000` talks to the API correctly in container topology.

| Gap | What happens |
|-----|----------------|
| Absolute `API_BASE` | Browser always calls host loopback `:8000`, not `https://host/api` via NGINX. Works for Windows local dual-process start; **breaks or bypasses** Compose (backend only `expose`d, not published). |
| WS `:8000` | Live gateway ignores NGINX `/api/v1/ws` upgrade proxy. Same local-dev bias. |
| NGINX correct, clients wrong | `nginx.conf` correctly proxies `/api/` and WS to `backend:8000`. Frontend never uses that path. |
| Multi-worker Dockerfile | `--workers 2` forks processes; each has its own `_sessions` dict → intermittent login/401 flapping under load balancer / round-robin. |
| Nested CI | Workflow lives under package `.github/` with `working-directory: Mercury_Enterprise_v16`, implying git-root placement, but git root has **no** `.github/` → CI does not run for the repo as structured. |
| Env bootstrap | Compose `env_file: .env` with no checked-in `.env.example` increases misconfiguration risk. |

**Net:** Artifacts exist (Dockerfiles, compose, nginx, CI YAML content), but they are **not an integrated production package**.

---

## 4. Authorization gaps (explained)

**What works (good foundation):**
- Session login/logout/session/context
- RBAC on incident **writes**, approvals, audit, reports, decisions, connector manage/read (connectors use explicit permission helpers)
- WebSocket requires a valid session cookie

**What does not:**

| Surface | Gap |
|---------|-----|
| `GET /incidents`, `GET /incidents/{id}`, assessment, report | No session / no permission / list not tenant-scoped → data exposure + IDOR across org/site |
| `GET /alerts` | Open read |
| `GET /dashboard/summary` | Optional session; usable unauthenticated |
| `GET /ops/health`, platform/integrations/compliance | Open diagnostics/surface |
| `POST /ops/coordinate` | **Unauthenticated write** into response orchestration |

Sensitive Milestone 1–2 paths (audit, reports, decisions, connector lifecycle) are largely gated; **legacy demo read surfaces and ops coordinate were left open**.

---

## 5. Intentional or bugs?

| Finding | Classification | Rationale |
|---------|----------------|-----------|
| Hardcoded `:8000` API/WS | **Intentional demo/dev convenience left unfinished** | Optimized for local `START_ALL` dual ports; never completed for NGINX same-origin |
| Nested CI / workers=2 | **Packaging oversight / incomplete hardening** | Not malicious; conflicts with in-memory sessions and repo layout |
| Open incident/alert/dashboard reads | **Mostly intentional historical demo openness** | Early UX favored open reads; org/site columns added later without closing GETs |
| `POST /ops/coordinate` unauthenticated | **Bug / security defect** | Write path without auth is not a documented demo feature and is unsafe |
| Demo auto-login + default password | **Intentional demo posture** | Explicit in `ensureSession` and config defaults; documented as must-remove for real deploy |
| No Alembic | **Known engineering shortcut** | Acceptable for SQLite demo; weak for Postgres lifecycle |
| Residual XSS | **Incomplete hardening** (partially fixed elsewhere) | Mix of leftover demo DOM and incomplete escape pass |
| In-memory decisions (Option A) | **Intentional Milestone 2 design choice** | Documented; audit durable, reviews ephemeral |

---

## 6. Are they blockers for production?

| Category | Blocker for production? |
|----------|-------------------------|
| Packaging (C1–C4, H2) | **Yes** — Compose/NGINX deploy unreliable; sessions broken under workers; CI invisible |
| Authorization (C5–C6, H1) | **Yes** — confidential incident data exposure; unauth ops write |
| Demo identity (C7–C8) | **Yes** for any non-lab network |
| DB migrations (H3) | **Yes** for managed Postgres upgrades; **waivable** for throwaway demo DB |
| XSS / Secure cookie (H4–H5) | **Yes** for browser-exposed prod |
| Perf unbounded lists (H6) | **Conditional** — blocker at scale; acceptable for tiny demo datasets |
| Simulated AI/feeds (M4) | **Yes** for safety-critical ops; **N/A** if scope is demo-only |

**For production (as asked): these are blockers.**  
**For internal RC demo on localhost with waivers: not all are blockers.**

---

## 7. Recommended fixes (if any)

Priority order for a production unblock (do **not** apply in this gate pass):

1. **Authz:** Require session + permissions on all incident GETs; enforce org/site filters; protect `/ops/coordinate` (and preferably ops health); close or gate alerts/dashboard sensitive fields.
2. **Identity:** Remove frontend auto-login; require strong `MERCURY_AUTH_PASSWORD`; default `SESSION_COOKIE_SECURE=true` behind TLS; plan OIDC.
3. **Packaging:** Set `API_BASE` to relative `/api/v1` (or `window.location.origin`); derive WS from page protocol/host/path (via NGINX); publish consistent topology.
4. **Workers/sessions:** `--workers 1` **or** shared session store (Redis) before multi-worker.
5. **CI:** Move/copy workflow to git-root `.github/workflows/ci.yml`.
6. **DB:** Introduce Alembic (or documented migration story) for Postgres; keep `create_all` for fresh envs only.
7. **Frontend security:** Escape all dynamic `innerHTML` insertions (`commandCenter.js`, `liveOps.js`, etc.).
8. **API hygiene:** Pagination/`limit` on list endpoints; add `.env.example`.

---

## 8. Security review

| Control | Assessment |
|---------|------------|
| Session cookie httponly | Present — good |
| RBAC on writes / audit / reports / decisions / connectors | Largely present — good foundation |
| Authz on sensitive reads / ops write | **Fail** |
| Demo credentials / auto-login | **Fail** for production |
| TLS / Secure cookie defaults | **Fail** by default |
| CORS allow-list | Present (localhost defaults) — tighten for prod origins |
| API key middleware | **Not enforced** — do not claim as control |
| XSS | **Partial fail** — residual sinks |
| Audit durability | Present for gated operator actions — good |
| Advisory-only decisions | Explicit `requires_human_approval` / no auto-execute — good invariant |
| Secrets in repo | Prefer env; ensure no production secrets committed; rotate demo password |

**Security verdict:** unsuitable for internet exposure or multi-tenant production without Critical/High remediation.

---

## 9. Performance review

| Topic | Assessment |
|-------|------------|
| Test suite speed | Fine for RC (~2s for 70 tests locally) |
| List APIs | Unbounded incident fetch — risk under growth |
| Dashboard | Loads all incidents for counts — O(n) memory/DB |
| In-memory rings | Alerts/timeline/decisions capped in places — good |
| Approvals / missions dicts | Unbounded growth risk |
| Multi-worker | Does not scale sessions/state correctly — false capacity |
| Load / soak / WS fan-out testing | **Not evidenced** |

**Performance verdict:** adequate for demo scale; **not proven** for production load.

---

## 10. Database review

| Topic | Assessment |
|-------|------------|
| Durable tables | `incidents`, `timeline_events`, `evidence`, `audit_events` |
| Engines | SQLite default; Postgres via Compose |
| Schema evolution | `create_all` + SQLite-only ALTER helpers — **Postgres upgrade gap** |
| Tenancy columns | Present on incidents/evidence/audit; **not enforced on open GETs** |
| Non-durable state | Sessions, decisions, approvals, many engines — restart loss / worker split |
| Backups | Documented in DR runbook; not automatically verified in this gate |
| Rollback schema | M2 additive APIs with no new tables — app rollback generally safe |

**Database verdict:** workable for RC demo; **incomplete** for production Postgres lifecycle and tenancy enforcement.

---

## 11. API review

| Topic | Assessment |
|-------|------------|
| Contract completeness (M1–M2) | Decisions, reports, audit, connectors, health/ready enriched — **present** |
| Consistency | Mixed auth posture (gated vs open) — **production fail** |
| Advisory metadata | Decision APIs enforce human-control messaging — **good** |
| Error/logging | Request IDs / timing — present |
| OpenAPI | Available at `/docs` for local |
| Breaking changes | Mostly additive vs prior packages — see release notes |
| WS auth | Session required — good; URL packaging still broken for Compose |

**API verdict:** feature-complete for RC scope; **not production-safe** until authz/packaging fixed.

---

## 12. Frontend review

| Topic | Assessment |
|-------|------------|
| Architecture | Vanilla JS modular — aligned with Mercury constraints |
| Syntax / modules | `node --check` pass on JS set |
| Deploy wiring | Absolute API + `:8000` WS — **production fail** |
| Demo auto-login | **production fail** |
| XSS hygiene | Improved in places; residuals remain |
| Decision Timeline UI | Present for Task 19 |
| Framework creep | None (no React/Vue) — good |

**Frontend verdict:** demo-ready locally; **not Compose/production-ready**.

---

## 13. Deployment readiness

| Check | Result |
|-------|--------|
| Local Windows SQLite path | Ready for demo |
| Compose reference files | Present |
| Compose client compatibility | **Not ready** (API/WS hardcoding) |
| Session safety under Dockerfile CMD | **Not ready** |
| CI as repo automation | **Not ready** (path) |
| Runbooks | Present (`docs/runbooks/*`) |
| Secrets / `.env.example` | Weak |
| Docker validation on gate host | Incomplete where Docker absent |
| Prod TLS / Secure cookies | Not defaulted |

**Deployment readiness: NO GO for production.**

---

## 14. Rollback readiness

| Check | Result |
|-------|--------|
| Deploy/upgrade/rollback runbook | Present |
| DR runbook | Present |
| Known checkpoints | Documented (`checkpoint-milestone-2-pre`, `c741e7f`, etc.) |
| Schema downgrade need (M2) | Low (no new M2 tables) |
| Audit preservation guidance | Explicit (do not wipe audit to “fix”) |
| In-memory state loss on rollback/restart | Expected — document for operators |

**Rollback readiness: GO for engineering RC** (procedures exist), with the caveat that production rollback of a never-production-ready package is secondary to not deploying it.

---

## 15. Final Go / No-Go recommendation

### Decision

```text
RELEASE STATUS: NO GO
```

**Mercury Enterprise V2.0 RC is not ready for production.**

It **is** acceptable to continue as an **engineering Release Candidate / controlled localhost demo** with explicit waivers of Critical packaging and authorization items — but that is **not** a production release.

### Production blockers (must clear before any GO)

1. **C1–C3** — Same-origin / proxied API + WebSocket for Compose/NGINX  
2. **C4** — Single worker or shared sessions  
3. **C5–C6** — Close open incident reads and unauthenticated ops coordinate  
4. **C7–C8** — Remove demo auto-login; eliminate default shared password in any deployed env  
5. **H2** — CI discoverable at git root (or restructure repo)  
6. **H4–H5** — Secure cookies under TLS; close residual XSS sinks  

### Gate actions explicitly not taken

- No code fixes applied in this pass  
- **No merge**  
- **No tag**  

---

**Signed gate outcome:** **NO GO** for production. Stopped after this report pending remediation approval or an explicit scope waiver to “demo-only RC.”
)
