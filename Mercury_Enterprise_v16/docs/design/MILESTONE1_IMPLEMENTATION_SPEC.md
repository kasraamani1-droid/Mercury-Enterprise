# Milestone 1 Implementation Specification

**Milestone:** Milestone 1 — Accountability, Historical Insight, Connector Resilience  
**Tasks:** 16 (Audit & Evidence Provenance), 17 (Historical Reporting & Analytics), 18 (Connector Lifecycle & Resilience)  
**Status:** CONTRACT — await human approval before checkpoint / implementation  
**Architecture constraints:** Vanilla JavaScript frontend, FastAPI backend, additive changes only. No redesign. No duplicate platforms. Preserve Tasks 12–15 behavior and backward-compatible APIs.

**Related contracts:**
- `APPLY_TASK_16.md` / `APPLY_TASK_17.md` / `APPLY_TASK_18.md`
- `docs/design/TASK16_IMPLEMENTATION_SPEC.md` (Task 16 detail contract — remains authoritative for Task 16)
- `docs/AI_ENGINEERING_WORKFLOW.md` (Engineering Gates)

**Current repo note (as of branch `task-16-audit-provenance`):** Task 16 application code exists as **uncommitted working-tree changes** after checkpoint `b26252f`. Milestone Phase 2 must complete/verify Task 16 per `TASK16_IMPLEMENTATION_SPEC.md` first, then implement Task 17, then Task 18. Do not start Task 17 until Task 16 validation passes.

---

## 1. Overall architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│  Frontend (vanilla JS workspaces — existing shells only)         │
│  Command | Executive | History | Admin | Integrations | …        │
└───────────────┬──────────────────────────────────────────────────┘
                │ /api/v1/*  (session cookie + RBAC)
┌───────────────▼──────────────────────────────────────────────────┐
│  FastAPI main.py + routers/connectors.py                         │
│  Auth/session (T13) · RBAC/approvals (T14) · Org/site (T15)      │
│  audit.py helpers (T16) · reporting aggregations (T17)           │
│  ConnectorManager (extended T18)                                 │
└───────────────┬──────────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────────┐
│  Persistence (minimal)                                           │
│  incidents (+ org/site for T17 scope) · timeline_events          │
│  evidence (+ provenance T16) · audit_events (T16)                │
│  SQLite ensure_schema() — no Alembic                             │
│                                                                  │
│  In-memory (reuse): sessions, approvals, AlertManager,           │
│  TimelineManager, ConnectorManager + health history ring (T18) │
└──────────────────────────────────────────────────────────────────┘
```

**Principles**
- One Mercury application; extend existing domains.
- Read models for reporting aggregate existing data (no second analytics DB).
- Connector lifecycle extends `ConnectorManager` (no second integration framework).
- Audit remains the durable attribution store; reporting and connector controls consume it where relevant.
- Human control: reporting/analytics/connector recovery never auto-execute operational actions.

---

## 2. Task 16 / 17 / 18 breakdown

### Task 16 — Audit Logging and Evidence Provenance (Module 11)

| Area | Deliverable |
|------|-------------|
| Durable audit | `audit_events` + `record_audit` / `list_audit_events` |
| Evidence | provenance / created_by / org / site columns |
| API | `GET /api/v1/audit` + write-path side effects |
| UI | Admin `#auditLog` server-backed; Command evidence meta |
| Authz | `audit.read` (Reviewer + Administrator) |
| Detail contract | Follow `docs/design/TASK16_IMPLEMENTATION_SPEC.md` exactly |

**Deferred by Task 16 (still deferred unless listed under Task 17/18 below):** EventBus audit mirror; History bind; Compliance legend; approval JSON org/site; seed `audit_events`; async purge; Alembic.

### Task 17 — Historical Reporting and Analytics (Module 12)

| Area | Deliverable |
|------|-------------|
| Read APIs | Minimal reporting endpoints aggregating incidents, audit, alerts, connectors, evidence provenance |
| Scope | Time range + session organization/site |
| Schema | Minimal `incidents.organization_id` / `incidents.site_id` (justified below) |
| UI | Executive KPIs/chart + History table + exports from real APIs |
| Authz | `reports.read` for Viewer, Operator, Reviewer (Administrator via `*`) |
| Provenance | Exports/history include provenance fields where evidence appears |

### Task 18 — Connector Lifecycle and Resilience (Module 13)

| Area | Deliverable |
|------|-------------|
| Manager | Extend `ConnectorManager` / `BaseConnector`: start/stop/recover, retry/backoff, degraded/error transitions, in-memory health history ring |
| API | Extend `/api/v1/connectors*` — no parallel integration API family |
| Audit | Lifecycle actions → `record_audit` |
| Reporting | Connector reliability metrics feed Task 17 summary |
| UI | Integrations + Command connector health panels; admin/operator controls |
| Authz | `connectors.read` (all authenticated roles); `connectors.manage` (Operator + Administrator) |

---

## 3. Dependency order (mandatory)

```text
Tasks 12–15 (complete foundations)
        ↓
Task 16 — Audit + evidence provenance
        ↓  (must pass tests / checklist)
Task 17 — Reporting/analytics (consumes audit + scoped incidents)
        ↓  (must pass tests / checklist)
Task 18 — Connector lifecycle (audited actions + reliability into reports)
        ↓
Milestone validation + MILESTONE1_IMPLEMENTATION_REPORT.md
```

**Rules**
1. Do not implement Task 17 features before Task 16 is complete and green.
2. Do not implement Task 18 features before Task 17 reporting endpoints exist (so connector reliability can plug into the same summary contract).
3. Within each task, follow that task’s file/function sequence; do not pull future-task work forward.

---

## 4. Exact files to modify

### Shared / Task 16 (per TASK16_IMPLEMENTATION_SPEC.md)

| Path | Task | Action |
|------|------|--------|
| `backend/app/core/config.py` | 16 | Modify |
| `backend/app/security/authorization.py` | 16/17/18 | Modify (permissions accumulate) |
| `backend/app/models.py` | 16/17 | Modify |
| `backend/app/schemas.py` | 16/17/18 | Modify |
| `backend/app/database.py` | 16/17 | Modify (`ensure_schema`) |
| `backend/app/audit.py` | 16 | Create / complete |
| `backend/app/main.py` | 16/17 | Modify |
| `backend/tests/test_audit.py` | 16 | Create / complete |
| `backend/tests/conftest.py` | 16 | Modify (schema/seed bootstrap) |
| `frontend/js/api.js` | 16/17/18 | Modify |
| `frontend/js/enterprise.js` | 16/17 | Modify |
| `frontend/js/incidents.js` | 16 | Modify |
| `frontend/js/app.js` | 16/17/18 | Modify |

### Task 17 additions

| Path | Action | Why necessary / why existing code insufficient |
|------|--------|------------------------------------------------|
| `backend/app/reporting.py` | **Create** (functions only) | Aggregation helpers; avoid bloating `main.py`. Not a separate analytics platform. Existing `dashboard/summary` mixes live ops widgets and lacks time-range/org/site report contracts and History export shape. |
| `backend/app/main.py` | Add report routes | Wire read-only reporting under `/api/v1`. |
| `backend/app/models.py` | Add incident org/site columns | Site-scoped historical KPIs cannot be correct without stamping incidents; session context alone does not filter unscoped rows. |
| `backend/tests/test_reporting.py` | **Create** | Task 17 acceptance tests. |
| `frontend/js/enterprise.js` | Bind Executive + History + exports | Today `historyRows` / `executiveData()` / hardcoded KPI HTML are demo-only. |
| `frontend/index.html` | **Minimal** — add/replace ids for Executive KPI values if needed (no new workspace) | Static `<b>14</b>` etc. cannot be updated without stable DOM ids. Prefer adding ids like `#execIncidentsToday` only; do not redesign layout. |
| `frontend/js/api.js` | `getReportSummary`, `getReportHistory` | Client access to new read APIs. |

### Task 18 additions

| Path | Action | Why necessary / why existing code insufficient |
|------|--------|------------------------------------------------|
| `backend/app/connectors/manager.py` | Extend | Lifecycle/retry/history belong here; creating a new manager would duplicate. Current manager lacks recover, backoff, health history, RBAC-aware ops. |
| `backend/app/connectors/base.py` | Extend start/stop/recover hooks | Providers already inherit `BaseConnector`. |
| `backend/app/connectors/models.py` | Extend record/health DTOs | Additive fields for retry counts, last state change, optional org/site tags. |
| `backend/app/routers/connectors.py` | Extend routes | Existing connector API family; do not create `/integrations-lifecycle` parallel stack. |
| `backend/tests/test_connectors.py` | Extend | Lifecycle/retry/RBAC/audit tests. |
| `frontend/js/enterprise8.js` | Extend Integrations catalog rendering | Existing Integrations shell; replace purely static catalog rows with API-backed lifecycle status where practical. |
| `frontend/js/app.js` | Map real connector health into Command panel | Today dashboard summary uses category placeholders; Task 18 aligns with live connector states. |
| `frontend/index.html` | **Minimal** only if Integrations needs a diagnostics container id | Prefer reuse `#integrationCatalog` / existing connector telemetry ids. |

### Explicitly do not create

- Second audit/analytics/connector platforms or managers named `*AnalyticsManager` / `*LifecycleManager` as parallel products
- New product tabs
- React/Vue/Angular/Next.js
- Alembic
- Duplicate `/api/v1/events` human-audit API
- Tasks 19–20 explainability / production hardening features

---

## 5. Existing classes / services / managers to reuse

| Component | Path | Reuse for |
|-----------|------|-----------|
| Session / `require_session` / `require_permissions` | `main.py`, `authorization.py` | All gated routes |
| Org/site catalogs + context | `main.py` | Report + connector scoping |
| `_approvals` + approval helpers | `main.py` | Unchanged Task 14; audited by Task 16 |
| `Incident` / `Evidence` / `TimelineEvent` | `models.py` | Domains + reporting inputs |
| `record_audit` / `list_audit_events` | `audit.py` | T16 + T18 lifecycle attribution; T17 provenance-aware exports |
| `AlertManager` | `alerts.py` | KPI inputs (ack/active counts) |
| `TimelineManager` | `timeline/` | Optional live counts only; not durable audit |
| `MissionService` | `missions/` | Optional mission KPI counts in summary |
| `ConnectorManager` / `registry` / providers | `connectors/` | Task 18 extension point |
| Platform `event_bus` | `events/bus.py` | Keep for observation events; do not overload as human audit |
| `GET /dashboard/summary` | `main.py` | Keep for Command live ops; Task 17 adds separate report endpoints rather than overloading this into History/Executive contracts |
| Workspaces | `index.html`, `enterprise.js`, `enterprise8.js` | Executive, History, Admin, Integrations |
| `listAudit` / session APIs | `api.js` | Frontend patterns |

---

## 6. Database / schema changes

### Task 16 (already specified — required)

| Change | Justification |
|--------|----------------|
| Table `audit_events` | Durable attribution; TimelineManager/EventBus/in-memory approvals are not durable or site-queryable for compliance review |
| Evidence columns `provenance`, `created_by`, `organization_id`, `site_id` | Structured provenance cannot be inferred safely from free-text `source` |

Migration: `ensure_schema()` + SQLite `ALTER` guards (no Alembic).

### Task 17 (required — minimal)

| Change | Nullable | Default | Justification |
|--------|----------|---------|---------------|
| `incidents.organization_id` | YES initially, stamped on create | `None` for legacy rows | Task 17 requires org/site scoped historical KPIs. Existing incidents have **no** site stamp; session filtering alone cannot scope legacy/global rows correctly. |
| `incidents.site_id` | YES initially, stamped on create | `None` | Same |

**Why existing code cannot satisfy Task 17 without this:** `GET /incidents` and seed data are unscoped; audit_events are site-scoped but do not replace incident KPI denominators (open/resolved counts, severity mix). Encoding site inside `summary` text is not queryable or enterprise-grade.

**Indexing:** index `organization_id`, `site_id` (and optionally `(site_id, created_at)` if cheap).

**Legacy rows:** Reports include only rows matching session org/site **or** explicitly document that unscoped legacy rows are excluded from site KPIs (preferred: exclude `NULL` site from site-scoped reports). Seed updates to stamp default east/CYUL.

### Task 18 (schema)

| Change | Decision |
|--------|----------|
| New SQL table for connector health | **Not required** if in-memory ring buffer (e.g. max 200 transitions per connector) + `audit_events` for human start/stop/recover satisfy diagnosability within process lifetime |
| Justification for avoiding table | Connectors are already in-process; Task 18 allows persist “where justified.” Durable operator intent is covered by Task 16 audit. Avoid unnecessary schema expansion. |
| If later durability is mandated | Ask before adding `connector_health_events` — out of default Milestone 1 scope |

### Migration strategy

Extend `ensure_schema()`:
1. `create_all` (audit_events, etc.)
2. SQLite ALTERs for evidence columns (Task 16)
3. SQLite ALTERs for incident org/site (Task 17)
4. Fallback: delete local SQLite DB and restart

---

## 7. API changes

### Task 16

| Endpoint | Change | Compatibility |
|----------|--------|---------------|
| `GET /api/v1/audit` | **New** | Additive |
| Auth/approval/incident/evidence writes | Audit side-effects | Response keys preserved except additive evidence fields |
| Evidence/report GET | Additive provenance fields | Backward compatible |

Detail: `TASK16_IMPLEMENTATION_SPEC.md` §7.

### Task 17 — new read-only endpoints (minimal family under `/api/v1/reports`)

**Why not only reuse `GET /dashboard/summary`?**  
Dashboard summary is a live Command ops widget mix (missions, connectors placeholders, decision timeline). Overloading it for Executive/History time-range reporting would break Command contracts or create ambiguous payloads. A small `/reports/*` family is incremental and reusable by Tasks 18–20 without a second gateway.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/v1/reports/summary` | session + `reports.read` | KPIs + trends for Executive |
| `GET` | `/api/v1/reports/history` | session + `reports.read` | Tabular history rows for History workspace / CSV |

**Query params (both):**
- `start` / `end` (ISO datetime, optional; default last 24h or 7d — specify in implementation as last 7 days)
- Scope **forced** from session `organization_id` / `site_id` (no client widen)

**`GET /reports/summary` response (illustrative contract):**
```json
{
  "organization_id": "...",
  "site_id": "...",
  "window": {"start": "...", "end": "..."},
  "kpis": {
    "incidents_total": 0,
    "incidents_open": 0,
    "incidents_resolved": 0,
    "resolution_rate": 0.0,
    "median_response_seconds": null,
    "audit_events": 0,
    "evidence_items": 0,
    "connector_online": 0,
    "connector_degraded": 0,
    "connector_error": 0
  },
  "trends": {
    "incidents_by_hour": [{"hour": "00", "count": 0}]
  },
  "provenance": {
    "simulated_evidence": 0,
    "operator_entered_evidence": 0,
    "system_generated_evidence": 0
  },
  "disclaimer": "Historical summary derived from Mercury operational data. Advisory only; no automated action."
}
```

**`GET /reports/history` response:** list of row objects mapping to History table columns, including operator attribution from audit when available, site id, severity/status from incidents, and provenance summary when evidence-linked.

**Errors:** `401` unauthenticated; `403` missing `reports.read`.

**Do not add:** separate analytics service host; GraphQL; duplicate incident list endpoint.

### Task 18 — extend existing connector routes

| Method | Path | Auth | Change |
|--------|------|------|--------|
| `GET` | `/api/v1/connectors` | session + `connectors.read` | Additive fields; optional site filter using session |
| `GET` | `/api/v1/connectors/{id}/health` | `connectors.read` | Additive diagnostics (retry count, last_transition) |
| `GET` | `/api/v1/connectors/{id}/health-history` | `connectors.read` | **New** — ring buffer history |
| `POST` | `/api/v1/connectors/{id}/start` | `connectors.manage` | **New** — human lifecycle |
| `POST` | `/api/v1/connectors/{id}/stop` | `connectors.manage` | **New** |
| `POST` | `/api/v1/connectors/{id}/recover` | `connectors.manage` | **New** — clear error → starting/online with backoff reset |
| `POST` | `/api/v1/connectors/{id}/poll` | `connectors.manage` (tighten from open) | Keep behavior; add retry/backoff; audit on failure/success as appropriate |

**Why existing routes insufficient:** Today list/health/poll exist but there is no start/stop/recover control surface, no health history API, no RBAC, and poll auto-starts without explicit operator lifecycle semantics.

**Compatibility:** Existing `GET /connectors` and `GET .../health` remain; response fields additive. Poll may gain stricter auth — document as intentional hardening compatible with Task 14 (open poll was a gap).

Lifecycle actions must call `record_audit` with actions such as `connector.start`, `connector.stop`, `connector.recover`, `connector.poll`.

---

## 8. Frontend / UI impact

| Workspace | Task | Change |
|-----------|------|--------|
| Admin Session audit | 16 | Server audit feed (already specified) |
| Command evidence | 16 | Provenance meta |
| Executive | 17 | KPI cards + hourly chart + export from `/reports/summary` |
| History | 17 | Replace demo `historyRows` with `/reports/history`; search/export against loaded data |
| Command connector panel | 18 | Reflect real connector states from connectors + summary |
| Integrations | 18 | Show lifecycle state/diagnostics; controls for manage-capable roles |
| Compliance / Cloud | — | No redesign; optional reliability numbers only if already displayed without new pages |

**No new product tabs.** Preserve Task 12 navigation.

---

## 9. Security and authorization impact

| Permission | Roles | Used by |
|------------|-------|---------|
| `audit.read` | Reviewer, Administrator (`*`) | Task 16 |
| `reports.read` | Viewer, Operator, Reviewer, Administrator | Task 17 |
| `connectors.read` | Viewer, Operator, Reviewer, Administrator | Task 18 reads |
| `connectors.manage` | Operator, Administrator | Task 18 start/stop/recover/poll |

**Rules**
- Forced site/org scope from session on audit, reports, and connector visibility filters where stamped.
- Unauthorized → explicit `401`/`403`.
- Connector manage actions are human-explicit and audited.
- Reporting outputs are read-only and must include advisory disclaimer text.
- No autonomous operational execution from analytics or connector recovery.

---

## 10. Risks

| Risk | Mitigation |
|------|------------|
| Task 16 WIP already in working tree | Phase 1 checkpoint; Phase 2 completes Task 16 first and validates before 17 |
| Legacy incidents without site | Exclude null site from scoped KPIs; re-seed/stamp defaults |
| Overloading dashboard/summary | Keep Command summary; add `/reports/*` |
| Connector in-memory history lost on restart | Accepted; operator actions durable via audit; ask before SQL health table |
| Tightening poll auth breaks anonymous demos | Use session + `connectors.manage`; update tests |
| Scope creep into Tasks 19–20 | Explicit out-of-scope list |
| Duplicate History semantics (audit vs incidents) | History rows primarily incident-scoped with audit attribution fields; Admin remains audit system of record |
| Frontend hardcoded Executive HTML | Minimal id injection only |

---

## 11. Test strategy

### Per-task tests

| Task | Suite | Coverage |
|------|-------|----------|
| 16 | `backend/tests/test_audit.py` | Per TASK16_IMPLEMENTATION_SPEC |
| 17 | `backend/tests/test_reporting.py` | KPI aggregation; time/site/org scope; 401/403; provenance counts; export payload fields |
| 18 | extend `backend/tests/test_connectors.py` | state transitions; degraded/error; retry/recover; health history; RBAC; audit actions |

### Regression (mandatory after each task and at milestone end)

```text
pytest -q backend/tests
python -m compileall backend/app
node --check frontend/js/api.js
node --check frontend/js/app.js
node --check frontend/js/enterprise.js
node --check frontend/js/incidents.js
node --check frontend/js/enterprise8.js
```

Preserve Task 12–15 behaviors: session, RBAC, approvals, org/site context, dashboard load.

### Manual

1. Task 16: Admin audit + evidence provenance + site switch + role denial  
2. Task 17: Executive KPIs match API; History search/export; Viewer can read reports; provenance in export  
3. Task 18: start/stop/recover visible; degraded/error messaging; Integrations diagnostics; audit shows connector actions; summary connector KPIs update  

---

## 12. Rollback strategy

1. Revert to Milestone 1 checkpoint tag/commit (Phase 1).  
2. If schema partially applied: reset local SQLite (`mercury.db`) or restore backup; restart.  
3. Re-run `pytest -q backend/tests` on restored tree.  
4. Do not force-push shared main/develop.  
5. Do not merge without explicit approval.

---

## 13. Definition of Done

Milestone 1 is **READY TO ACCEPT** only when all are true:

1. Approved `MILESTONE1_IMPLEMENTATION_SPEC.md` followed with no unapproved deviations.  
2. Phase 1 checkpoint created before milestone implementation continues.  
3. Task 16 complete per `TASK16_IMPLEMENTATION_SPEC.md` and tests green.  
4. Task 17 complete: scoped reports APIs; Executive/History real data; exports; `reports.read` enforced.  
5. Task 18 complete: ConnectorManager lifecycle/resilience; extended connector APIs; audited manage actions; UI diagnostics on existing surfaces; reliability reflected in reports summary.  
6. Full pytest suite green; compileall + node checks green.  
7. Tasks 12–15 regression checked.  
8. `docs/design/MILESTONE1_IMPLEMENTATION_REPORT.md` produced with required sections and final status.  
9. No merge/push without explicit human approval.  
10. No autonomous execution/decision-making introduced.

---

## 14. Implementation sequence after approval

### PHASE 1 — Checkpoint
1. `git status` / `git diff --stat`  
2. Create/verify branch (e.g. `milestone-1-tasks-16-18` or continue `task-16-audit-provenance`)  
3. Checkpoint commit **and** annotated tag `checkpoint-milestone-1-pre` capturing current approved-spec baseline before further Task 17/18 coding  
4. If Task 16 code is already present uncommitted: either include a “Task 16 implementation” commit immediately after checkpoint (still before Task 17), or fold Task 16 completion into Phase 2 step A — **must not** start Task 17 until Task 16 is committed or clearly completed and tested

### PHASE 2 — Implement in order
1. **Task 16** — finish/verify exactly per `TASK16_IMPLEMENTATION_SPEC.md`  
2. **Task 17** — reporting module, incident site columns, `/reports/*`, Executive/History UI, tests  
3. **Task 18** — connector lifecycle/resilience, routes, UI, reporting KPI hookup, tests  
4. On material deviation → **STOP and ask**

### PHASE 3 — Validate
- Full pytest; compileall; node checks; API tests; T12–15 regression; manual checks

### PHASE 4 — Report
- Write `docs/design/MILESTONE1_IMPLEMENTATION_REPORT.md`  
- Final status `READY TO ACCEPT` or `NOT READY`  
- **Do not merge. Do not push without explicit approval.**

---

## 15. Out of scope (Milestone 1)

- Tasks 19–20 (explainability, production hardening)  
- Alembic / immutable signed ledger  
- Second analytics or connector platforms  
- Durable SQL connector health table (unless approved mid-flight)  
- Architecture redesign / SPA frameworks  
- Autonomous recovery that executes operational missions/decisions  
- Rewriting Mission/Fusion/Decision engines  

---

## Document control

| Field | Value |
|-------|-------|
| Path | `docs/design/MILESTONE1_IMPLEMENTATION_SPEC.md` |
| Tasks | 16, 17, 18 |
| Next gate | Human approval → Phase 1 checkpoint → Phase 2 implementation |
