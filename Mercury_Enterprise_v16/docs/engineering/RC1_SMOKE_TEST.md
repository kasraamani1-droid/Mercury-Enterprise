# Mercury Platform RC1 — End-to-End Smoke Test Report

**Blocker:** RC1 Release Blocker 06  
**Date:** 2026-08-17  
**Method:** Sequential FastAPI `TestClient` walk of the 21 existing workflows + static UI surface checks. No Playwright browser driver. No new product features.

**Suite:** `backend/tests/test_rc1_e2e_smoke.py`  
**Result:** `2 passed` (UI surfaces + sequential 21-step API chain)

## Verdict

| Question | Answer |
|----------|--------|
| Do existing APIs work together in sequence? | **Yes** (login → org → domains → logout) |
| Is every workflow a complete UI+API product path? | **No** |
| Browser E2E (Playwright)? | **Not run** (RB-08 still open) |
| **Mercury Platform RC1** | **NO-GO** |

**Overall RC readiness: 77%**  
(Previously ~75%. Sequential smoke + Sign out UI already present. Still capped by identity durability RB-04 and incomplete workflows.)

## How the smoke was executed

1. Static UI: `frontend/index.html`, `app.js`, `api.js`, UX2 registry/workspaces, Command notification center.
2. Sequential API: one cookie session, workflows 1→21 in order (later steps reuse aircraft/org from earlier steps).
3. Existing domain pytest (**575 passed, 1 skipped**; QA-1 seed test green): fleet, components, planning, work orders, logistics, marketplace, twin, platform, reporting, audit, decisions.
4. `node --check` on workflow JS: **pass**.

Anonymous calls return 401. Empty aircraft create returns 422. Viewer cannot enqueue platform notifications (403). Logout clears the session.

## Passed workflows

Existing happy path works together (API + backend + DB + navigation surface). Product limits are noted, not treated as smoke breakage.

| # | Workflow | Evidence | Residual (does not fail smoke) |
|---|----------|----------|--------------------------------|
| 1 | Login | Overlay + `POST /auth/login`; wrong password 401; HttpOnly cookie | Identity still in-memory `operator_store` (RB-04) |
| 2 | Organization selection | `#organizationSelect`, `GET /organizations`, `POST /auth/context`; west org rejected | Org portal is read-heavy |
| 4 | Dashboard | Home workspace + `GET /dashboard/summary` + planning dashboard | Global summary still mixes SIM Command KPIs |
| 5 | Aircraft | Workspace + list/detail + SQL row; 422 on empty create | No inline edit/delete in UX2 |
| 6 | Fleet | Fleet workspace + `GET /fleet/fleets` | Cards, not fleet CRUD UI |
| 8 | Inventory | Inventory workspace + logistics dashboard/stock balances | Mutations live in Logistics Ops |
| 9 | Planning | Legacy planning workspace + due-list/programs | Dense grid |
| 10 | Work Orders | WO workspace + orders filtered by aircraft from step 5 + WO dashboard | Seed package `WP-DEMO-001` missing (see Failed tests) |
| 11 | Engineering | Engineering workspace + AD/SB/EO list APIs | Read-only board |
| 12 | Logbook | Logbook workspace + `GET /maintenance/logbook?aircraft_id=` | Writes via MRO release |
| 13 | Marketplace | Marketplace workspace + products/overview | Payments `not_configured`; quote UX uses `prompt()` |
| 14 | Digital Twin | Asset twin workspace + `GET /twin/twins` | Ops Twin (SIM) is a separate surface |
| 16 | Search | Palette trigger + `POST /platform/search/index` + `GET /platform/search?q=smoke` | SQL ILIKE; Command palette is not a dedicated results page |
| 18 | Reporting | `GET /reports/summary` + history; Command JSON download control | Incident/audit KPIs only — no AEOS WO/fleet report pack |
| 20 | Audit Trail | Admin `#auditLog`; `GET /audit` as Reviewer; SQL `audit_events` | Operator role has no `audit.read` (existing RBAC) |
| 21 | Logout | `#ux2SignOut` → `signOut()` → `POST /auth/logout`; subsequent GETs 401 | Canvas RB-06 was stale; Sign out is wired |

## Failed workflows (complete RC path)

These APIs exist, but the **end-to-end operator journey is incomplete or simulated**. Counted as failed for “complete E2E validation.”

| # | Workflow | Why it fails complete E2E | What still works |
|---|----------|---------------------------|------------------|
| 3 | RBAC | Admin `#roleSelect` is **client-only** (“Commander/Supervisor/…”). It does not change the session. No permission-matrix UI. | `GET /platform/rbac/matrix` + templates; viewer 403 on manage |
| 7 | Components | **No `componentWorkspace`**. Catalog/serialized APIs have no list/install UI; object shell only. | `GET /components/catalog` and `/serialized` 200 |
| 15 | Notifications | `#notificationCenter` is an **in-memory** Command array (`const notifications=[]`). Home KPIs call the platform API; the center does not. | `GET/POST /platform/notifications` + mark read |
| 17 | File Uploads | **No `type="file"`** in `index.html`. UI cannot pick bytes. | `POST /platform/files` (URI metadata) and `/files/upload` (multipart API) |
| 19 | AI Assistant | Copilot is **rules-based DEMO templates** (`copilot.js`). AI workspace is a static advisory card. No LLM. Decisions are in-memory. | `POST /decisions/evaluate` advisory payload; AI index stubs list |

## Dimension checklist (system)

| Dimension | Sequential smoke | Notes |
|-----------|------------------|-------|
| UI | Partial | Strong on MRO/aircraft; shells/stubs on components, files, AI, RBAC admin |
| API | Pass | All 21 steps reachable on existing routes |
| Backend | Pass | FastAPI routers + services |
| Database | Pass | Aircraft and audit rows via SQLAlchemy |
| Permissions | Pass on APIs | Viewer 403; Operator cannot read `/audit` |
| Validation | Pass | 422 empty aircraft; 401 anonymous |
| Audit logging | Pass | Login/domain audits in SQL; list API is Reviewer/Admin |
| Error handling | Pass | 401/403/422 as designed |
| Navigation | Pass static | UX2 registry IDs match workspace sections |
| Integration | Pass | WO list uses aircraft id from step 5; search indexes that aircraft; files attach to it; logout invalidates the same cookie |

## Existing tests (this run)

```
575 passed, 1 skipped (live PostgreSQL via MERCURY_TEST_DATABASE_URL)
```

**QA-1 (seed work package):** `test_work_orders_execution.py::test_seed_work_package_and_job_card` is green. Demo rows `WP-DEMO-001` / `JC-DEMO-001` are seeded idempotently (`wp-demo-c-gmea`, `jc-demo-oil`) and asserted by id plus aircraft-filtered list. Do not treat as an open CI failure.

Frontend `node --check` on tracked `frontend/js/**/*.js` (excluding gitignored `config.local.js`): **pass**. Local override template uses JavaScript comments.

Playwright was **not** added (would be a new test stack / RB-08).

## Remaining RC blockers

| ID | Status | Notes |
|----|--------|--------|
| RB-01 Tenant incident IDOR | Resolved | |
| RB-02 WebSocket tenant leak | Resolved | |
| RB-03 Approval persistence | Resolved | |
| **RB-04 Identity durability** | **Open — P0** | Login still `operator_store`; OrgUser unused |
| RB-05 Argon2id | Resolved | |
| RB-06 Sign out UI | **Resolved (already in tree)** | `#ux2SignOut` + `signOut()`; operator field not prefilled |
| RB-07 Redis required | Open | Multi-worker still unsafe |
| RB-08 Playwright browser E2E | Open | This blocker delivered API+static smoke only |
| **QA-1 CI seed / pipeline** | **Closed** | Full pytest green; see [CI.md](CI.md) |

Other product Holds from the 21-workflow scorecard (components UI, files, notifications binding, AI, fake admin roles) remain **out of Platform 1.0** unless explicitly scoped.

## GO / NOT GO

| Gate | Decision |
|------|----------|
| Sequential API smoke of existing functionality | **GO** |
| Complete 21-workflow product E2E | **NO-GO** (5 failed complete paths) |
| **Tag `v1.0.0-rc.1`** | **NO-GO** |

Do not tag RC1 until at least RB-04 is closed. Playwright (RB-08) before any customer-facing pilot.

## How to re-run

```powershell
cd backend
$env:MERCURY_ENV="development"
$env:MERCURY_AUTH_PASSWORD="ci-test-password-not-for-production"
python -m pytest -q tests/test_rc1_e2e_smoke.py
```

Related: [FINAL_RELEASE_GUIDE.md](../FINAL_RELEASE_GUIDE.md), [PRODUCTION_READINESS.md](../ux/PRODUCTION_READINESS.md).
