# Task 16 Implementation Specification

**Module:** 11 — Audit Logging and Evidence Provenance  
**Source task:** `APPLY_TASK_16.md`  
**Status:** CONTRACT — implementation must follow this document exactly  
**Architecture:** Preserve vanilla JavaScript frontend, FastAPI backend, existing API contracts, data flow, folder structure, routing, and UI layout. Additive changes only.

---

## 1. Objective

Add enterprise audit logging and evidence provenance to the existing Mercury platform so operators and reviewers can inspect **who did what, when, from what source/origin, and in what organization/site context**, without redesigning the application or introducing a second audit/history subsystem.

Human operators remain fully in control. Audit and provenance are **traceability features only** — they must not introduce autonomous execution or autonomous decision making.

This task builds on:

- Task 12 — dashboard / workspace shell
- Task 13 — authentication and session context
- Task 14 — RBAC and approval model
- Task 15 — organization/site scoping

---

## 2. Scope

### In scope

1. Durable `audit_events` table for auditable operator and system-visible actions.
2. Evidence provenance and attribution columns on existing `evidence` table.
3. Thin helper module `backend/app/audit.py` (functions only — not an AuditManager platform).
4. Permission `audit.read` for Reviewer (Administrator covered by `*`).
5. New read endpoint `GET /api/v1/audit` (site-scoped, role-gated, retention filtered).
6. Side-effect instrumentation of existing auth, approval, incident, event, and evidence write paths.
7. Additive evidence/report JSON fields for provenance and attribution.
8. Admin workspace Session audit UI backed by `GET /api/v1/audit`.
9. Command workspace evidence meta display of provenance fields.
10. Refresh Admin audit list after organization/site context change.
11. SQLite startup schema guard for existing databases.
12. Backend tests for audit, provenance, RBAC, site scope, and regression of Tasks 13–15.

### Canonical constants

| Kind | Allowed values |
|------|----------------|
| `origin` | `operator`, `system`, `simulated` |
| `provenance` | `simulated`, `operator_entered`, `system_generated` |
| `outcome` | `success`, `denied`, `failed` |
| Audit `source` | `api`, `seed`, `system` |

### Canonical audit `action` values

| Action | When recorded |
|--------|----------------|
| `auth.login` | Successful login |
| `auth.logout` | Logout when a valid session existed |
| `auth.context` | Successful org/site context update |
| `approval.request` | Approval request created |
| `approval.approve` | Approval approved |
| `approval.consume` | Approved approval consumed on resolve/close |
| `incident.create` | Incident created |
| `incident.status` | Incident status updated |
| `incident.event` | Incident timeline event added |
| `incident.evidence` | Evidence added |

### Default seed site context

- `organization_id`: `org-aviation-east`
- `site_id`: `site-cyul`

### Retention

- Filter-on-read using `settings.audit_retention_days` (env `MERCURY_AUDIT_RETENTION_DAYS`, default `365`).
- No asynchronous purge job in this task.

---

## 3. Out of scope

Do **not** implement any of the following without an explicit change request and spec amendment:

| Item | Reason |
|------|--------|
| EventBus / TimelineManager audit mirror | Would create a second live history channel |
| Additive `organization_id` / `site_id` on approval HTTP JSON responses | Not required; stamp in memory for audit writes only |
| History workspace `#historyBody` binding to audit API | Deferred; leave demo `historyRows` unchanged |
| Compliance workspace provenance legend HTML changes | Deferred |
| Seed inserts into `audit_events` | Deferred |
| Async retention purge / deletion job | Deferred |
| `organization_id` / `site_id` columns on `incidents` | Deferred (beyond minimum audit/provenance need) |
| Alembic or full migration framework | Deferred |
| Durable SQL approvals table | Deferred; keep Task 14 in-memory `_approvals` |
| New product tabs / second audit dashboard | Forbidden by task |
| New AuditManager class / audit microservice | Forbidden parallel subsystem |
| Overloading `GET /api/v1/events` as human audit API | Wrong bus; duplicate history semantics |
| React / Vue / Angular / Next.js or other SPA frameworks | Architecture violation |
| Autonomous execution, targeting, or weapon control | Safety prohibition |

---

## 4. Files to modify

| Path | Action |
|------|--------|
| `backend/app/core/config.py` | Modify |
| `backend/app/security/authorization.py` | Modify |
| `backend/app/models.py` | Modify |
| `backend/app/schemas.py` | Modify |
| `backend/app/database.py` | Modify |
| `backend/app/audit.py` | **Create** |
| `backend/app/main.py` | Modify |
| `backend/tests/test_audit.py` | **Create** |
| `backend/tests/test_api.py` | Modify only if an existing assertion breaks |
| `frontend/js/api.js` | Modify |
| `frontend/js/enterprise.js` | Modify |
| `frontend/js/incidents.js` | Modify |
| `frontend/js/app.js` | Modify |
| `frontend/index.html` | **Do not modify** |
| `docs/design/TASK16_IMPLEMENTATION_SPEC.md` | This contract (created before implementation) |

No other files may be changed unless required to fix a defect discovered while implementing this contract — and only within the listed set, or after asking.

---

## 5. Functions to modify

### 5.1 Config — `backend/app/core/config.py`

| Symbol | Change |
|--------|--------|
| `Settings` | Add `audit_retention_days: int = _int("MERCURY_AUDIT_RETENTION_DAYS", 365)` |

### 5.2 Authorization — `backend/app/security/authorization.py`

| Symbol | Change |
|--------|--------|
| `PERMISSIONS_BY_ROLE[Role.REVIEWER]` | Add `"audit.read"` |
| `PERMISSIONS_BY_ROLE[Role.ADMINISTRATOR]` | Unchanged (`"*"`) |
| `PERMISSIONS_BY_ROLE[Role.OPERATOR]` | Unchanged (no `audit.read`) |
| `PERMISSIONS_BY_ROLE[Role.VIEWER]` | Unchanged |
| `parse_role`, `has_permissions` | Unchanged |

### 5.3 Models — `backend/app/models.py`

| Symbol | Change |
|--------|--------|
| `Evidence` | Add columns `provenance`, `created_by`, `organization_id`, `site_id` |
| `AuditEvent` | **New class** → table `audit_events` |
| `uid`, `Incident`, `TimelineEvent` | Unchanged |

### 5.4 Schemas — `backend/app/schemas.py`

| Symbol | Change |
|--------|--------|
| `EvidenceCreate` | Optional `provenance: str \| None = None` (do not accept client `created_by` / org / site) |
| `EvidenceOut` | Always expose `provenance`, `created_by`, `organization_id`, `site_id` |
| `AuditEventOut` | **New class** for audit list responses |

### 5.5 Database — `backend/app/database.py`

| Symbol | Change |
|--------|--------|
| `ensure_schema()` | **New function**: `create_all` + SQLite conditional `ALTER TABLE evidence` for missing columns + optional indexes |

### 5.6 Audit helpers — `backend/app/audit.py` (new file)

| Symbol | Kind |
|--------|------|
| Provenance/origin constants + `ALLOWED_PROVENANCE` | Constants |
| `normalize_provenance(value, *, default=...)` | **New** — invalid value → HTTP 400 |
| `record_audit(db, **fields) -> AuditEvent` | **New** — `db.add` only; caller commits (except auth/approval routes that commit audit alone) |
| `list_audit_events(db, *, organization_id, site_id, action=None, target_id=None, limit=100, retention_days=None)` | **New** — forced site filter, retention filter, limit clamp 1..500, order `occurred_at DESC` |

**Forbidden in this module:** `AuditManager` class; EventBus/TimelineManager publishing.

### 5.7 API application — `backend/app/main.py`

| Symbol | Change |
|--------|--------|
| `lifespan` | Call `ensure_schema()` instead of bare `Base.metadata.create_all` |
| `login` | Add `db`; best-effort `record_audit(action="auth.login")` + commit; never fail login on audit error |
| `logout` | Validate session before invalidate; best-effort `auth.logout` audit |
| `update_session_context` | Capture old org/site; after update best-effort `auth.context` audit |
| `_create_approval` | Store internal `organization_id`, `site_id` on approval dict (not exposed in HTTP JSON) |
| `create_approval_request` | Add `db`; audit `approval.request`; commit; **response keys unchanged** |
| `approve_request` | Add `db`; audit `approval.approve`; commit; **response keys unchanged** |
| `create_incident` | Capture session via `Depends(require_permissions("incident.create"))`; audit `incident.create` in same commit |
| `update_incident_status` | Audit `incident.status`; if approval consumed, also audit `approval.consume` |
| `add_event` | Capture session; audit `incident.event` |
| `add_evidence` | Server-stamp provenance/created_by/org/site; audit `incident.evidence` |
| `incident_report` | Additive evidence keys: `provenance`, `created_by`, `organization_id`, `site_id` |
| `seed_demo` | Seed evidence with `provenance="simulated"`, `created_by="seed"`, default east/CYUL; **do not** seed `audit_events` |
| `list_audit` | **New route handler** for `GET /api/v1/audit` |

**Commit policy:**

- Incident/event/evidence/status: one commit including business row + audit row(s).
- Approvals: audit commit in route (approvals remain in-memory).
- Auth login/logout/context: best-effort audit commit; operational auth success must not depend on audit DB.

### 5.8 Frontend

| File | Symbol | Change |
|------|--------|--------|
| `frontend/js/api.js` | `listAudit({ action, target_id, limit } = {})` | **New export** → `GET /audit` |
| `frontend/js/enterprise.js` | `loadServerAudit`, `refreshEnterpriseAudit` | **New** |
| `frontend/js/enterprise.js` | `renderAudit` | Render server audit list into `#auditLog` |
| `frontend/js/enterprise.js` | `#downloadAudit` handler | Download server audit JSON |
| `frontend/js/enterprise.js` | `showWorkspace` | When `admin`, call `loadServerAudit()`; do not feed `#auditLog` from local `addAudit` |
| `frontend/js/enterprise.js` | `renderHistory` / `historyRows` | **Unchanged** (deferred) |
| `frontend/js/incidents.js` | `renderEvidence` | Show provenance · created_by · site_id · type · source · confidence |
| `frontend/js/app.js` | `onOrganizationChange`, `onSiteChange` | After context update, call `refreshEnterpriseAudit()` |

---

## 6. Database schema changes

### 6.1 New table: `audit_events`

| Column | Type | Nullable | Default | Index |
|--------|------|----------|---------|-------|
| `id` | `String` PK | NO | `uid()` | PK |
| `occurred_at` | `DateTime` | NO | `datetime.utcnow` (same pattern as existing models) | YES |
| `action` | `String(80)` | NO | — | YES |
| `actor` | `String(120)` | NO | — | NO |
| `actor_role` | `String(40)` | NO | `""` | NO |
| `organization_id` | `String(80)` | NO | — | YES |
| `site_id` | `String(80)` | NO | — | YES |
| `target_type` | `String(40)` | YES | `None` | NO |
| `target_id` | `String(120)` | YES | `None` | NO |
| `source` | `String(80)` | NO | `"api"` | NO |
| `outcome` | `String(40)` | NO | `"success"` | NO |
| `origin` | `String(40)` | NO | `"operator"` | NO |
| `details` | `Text` | NO | `""` | NO |

### 6.2 Altered table: `evidence`

| Column | Type | Nullable | Default | Index |
|--------|------|----------|---------|-------|
| `provenance` | `String(40)` | NO | `"operator_entered"` | NO |
| `created_by` | `String(120)` | NO | `""` | NO |
| `organization_id` | `String(80)` | YES | `None` | YES |
| `site_id` | `String(80)` | YES | `None` | YES |

Existing evidence columns remain unchanged.

### 6.3 Migration strategy (existing SQLite)

Implemented by `ensure_schema()` on startup:

1. `Base.metadata.create_all(bind=engine)` — creates `audit_events` if missing.
2. If SQLite: `PRAGMA table_info(evidence)`.
3. For each missing column, run:
   - `ALTER TABLE evidence ADD COLUMN provenance VARCHAR(40) NOT NULL DEFAULT 'operator_entered'`
   - `ALTER TABLE evidence ADD COLUMN created_by VARCHAR(120) NOT NULL DEFAULT ''`
   - `ALTER TABLE evidence ADD COLUMN organization_id VARCHAR(80)`
   - `ALTER TABLE evidence ADD COLUMN site_id VARCHAR(80)`
4. Optional: `CREATE INDEX IF NOT EXISTS` on `evidence.organization_id` and `evidence.site_id`.
5. Fallback for broken local demos: delete configured SQLite file (e.g. `mercury.db`) and restart to re-seed.

**Not in this task:** Alembic; Postgres auto-ALTER; approvals table; incident org/site columns.

---

## 7. API changes

### 7.1 New endpoint

#### `GET /api/v1/audit`

- **Auth:** session required + permission `audit.read`
- **Query params:**

| Param | Required | Default | Notes |
|-------|----------|---------|-------|
| `action` | no | omit | exact match filter |
| `target_id` | no | omit | exact match filter |
| `limit` | no | `100` | clamped to `1..500` |

- **Must not** accept `organization_id` or `site_id` query params (scope forced from session).
- **Request body:** none
- **Response `200`:** `list[AuditEventOut]`

```json
[
  {
    "id": "...",
    "occurred_at": "2026-08-10T12:00:00",
    "action": "incident.create",
    "actor": "operator",
    "actor_role": "Operator",
    "organization_id": "org-aviation-east",
    "site_id": "site-cyul",
    "target_type": "incident",
    "target_id": "...",
    "source": "api",
    "outcome": "success",
    "origin": "operator",
    "details": "..."
  }
]
```

- **Errors:** `401` unauthenticated; `403` missing `audit.read` (Viewer, Operator)
- **Retention:** exclude rows older than `audit_retention_days`
- **Ordering:** `occurred_at` descending

### 7.2 Modified endpoints (side-effects and/or additive fields)

| Method | Path | Request change | Response change | Compatibility |
|--------|------|----------------|-----------------|---------------|
| `POST` | `/api/v1/auth/login` | none | none | audit side-effect only (best-effort) |
| `POST` | `/api/v1/auth/logout` | none | none | audit side-effect only (best-effort) |
| `POST` | `/api/v1/auth/context` | none | none | audit side-effect only (best-effort) |
| `POST` | `/api/v1/approvals` | none | **keys unchanged** | audit side-effect; internal org/site stamp |
| `GET` | `/api/v1/approvals` | none | **keys unchanged** | no JSON expansion in this task |
| `POST` | `/api/v1/approvals/{approval_id}/approve` | none | none | audit side-effect |
| `POST` | `/api/v1/incidents` | none | none | audit side-effect |
| `PATCH` | `/api/v1/incidents/{incident_id}/status` | none | none | audit (+ consume) side-effect |
| `POST` | `/api/v1/incidents/{incident_id}/events` | none | none | audit side-effect |
| `POST` | `/api/v1/incidents/{incident_id}/evidence` | optional `provenance` | additive provenance fields | backward compatible |
| `GET` | `/api/v1/incidents/{incident_id}` | none | nested evidence additive fields | backward compatible |
| `GET` | `/api/v1/incidents/{incident_id}/report` | none | evidence[] additive keys | old keys preserved |

#### Evidence create request (compatible)

```json
{
  "evidence_type": "operator_note",
  "source": "Operator Console",
  "title": "...",
  "content": "...",
  "confidence": 80,
  "provenance": "operator_entered"
}
```

`provenance` optional; server default `operator_entered`. Invalid provenance → `400`.

Server always stamps: `created_by` (session operator), `organization_id`, `site_id`.

#### Evidence response additive fields

`provenance`, `created_by`, `organization_id`, `site_id` — existing fields unchanged.

### 7.3 Breaking changes

**None.** No existing fields removed or renamed. No existing routes removed.

---

## 8. UI changes

| Surface | DOM / module | Change |
|---------|--------------|--------|
| Admin → Session audit | `#adminWorkspace`, `#auditLog`, `#downloadAudit`, `enterprise.js` | Load/render/download from `GET /api/v1/audit`; 403 shows insufficient-permissions message |
| Command → Evidence details | `#evidenceDetails`, `incidents.js` `renderEvidence` | Display provenance, created_by, site_id with existing meta |
| Shell org/site selectors | `app.js` | Refresh Admin audit after context change |
| History | `#historyBody`, `historyRows` | **No change** |
| Compliance | `#complianceWorkspace` | **No change** |
| `frontend/index.html` | — | **No change** |
| SIM camera wall in evidence tab | decorative feeds | **No change** |

No new product tabs. No second audit dashboard page.

---

## 9. Test plan

### 9.1 New backend tests — `backend/tests/test_audit.py`

| Test function | Asserts |
|---------------|---------|
| `test_audit_created_on_incident_create_with_operator_attribution` | Durable audit row; actor/role from session |
| `test_approval_trail_request_approve_and_consume` | `approval.request`, `approval.approve`, `approval.consume` attributable |
| `test_evidence_provenance_and_site_stamp` | provenance/created_by/org/site on evidence |
| `test_audit_list_is_site_scoped` | Site A records not visible after switch to site B |
| `test_audit_read_forbidden_for_viewer` | `403` |
| `test_audit_read_forbidden_for_operator` | `403` |
| `test_audit_read_allowed_for_reviewer` | `200` |
| `test_audit_read_allowed_for_admin` | `200` |
| `test_audit_unauthorized_without_session` | `401` |
| `test_seed_evidence_provenance_is_simulated` | Seed evidence `provenance == "simulated"` |

Reuse demo operators: `admin`, `operator`, `reviewer`, `viewer` / password `mercury-demo`. Copy `login_as` helper locally in `test_audit.py` (avoid broad test refactor).

### 9.2 Regression

```text
pytest -q backend/tests/test_api.py
pytest -q backend/tests
```

Must keep passing Task 13 session tests, Task 14 RBAC/approval tests, Task 15 context tests, and other existing suites (`test_timeline`, `test_alerts`, `test_ops`, `test_decision_engine`, `test_missions`, `test_fusion`, `test_ai`, `test_connectors`).

### 9.3 Syntax / compile checks

```text
python -m compileall backend/app
node --check frontend/js/api.js
node --check frontend/js/enterprise.js
node --check frontend/js/incidents.js
node --check frontend/js/app.js
```

### 9.4 Manual validation

1. Start stack; frontend loads.
2. As `operator`: create incident + evidence; evidence meta shows provenance.
3. As `reviewer`/`admin`: Admin → Session audit shows site-scoped rows; download works.
4. Switch site: audit list changes.
5. As `viewer`: Admin audit shows insufficient permissions.
6. History still shows demo rows.
7. No new workspace tabs; existing Command/Admin shells intact.

---

## 10. Rollback plan

1. Revert the Task 16 branch / commits (restore pre-checkpoint tree).
2. If schema partially applied: delete local SQLite DB file used by `DATABASE_URL` (commonly `mercury.db`) and restart to recreate clean schema for the restored code, **or** keep DB only if restored code matches remaining columns.
3. Restart backend and frontend.
4. Confirm regression: `pytest -q backend/tests` on restored tree.
5. Do **not** force-push shared main/master unless explicitly requested.

---

## 11. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Existing SQLite missing new evidence columns | Runtime errors on evidence read/write | `ensure_schema()` ALTER guard; documented DB reset fallback |
| Audit DB failure blocks login | Auth outage | Best-effort audit on auth paths only |
| Operator/Viewer opens Admin audit | Confusion / error noise | Explicit insufficient-permissions message |
| Double-commit / partial writes | Inconsistent audit vs business row | Single commit policy for operational writes |
| Scope creep into History/Compliance/EventBus | Duplicate history paths | Out-of-scope table; ask before any deviation |
| Task 15 incident list still not site-filtered | Audits site-aware but incident archive is not | Accepted; deferred incident site columns |
| Local `addAudit` vs server audit confusion | Fake audit appears authoritative | `#auditLog` must render server data only |

---

## 12. Validation checklist

Use this checklist before declaring Task 16 complete:

- [ ] Checkpoint commit created before implementation
- [ ] Implementation matches this document with no unapproved deviations
- [ ] `audit_events` table exists and receives rows for instrumented actions
- [ ] Evidence rows include `provenance`, `created_by`, `organization_id`, `site_id`
- [ ] Seed evidence marked `provenance=simulated`
- [ ] `GET /api/v1/audit` enforces session site scope
- [ ] Reviewer and Administrator can read audit (`200`)
- [ ] Operator and Viewer cannot read audit (`403`)
- [ ] Unauthenticated audit read returns `401`
- [ ] Existing auth/session endpoints still behave (Task 13)
- [ ] Existing RBAC/approval flows still behave (Task 14)
- [ ] Existing org/site context update still behaves (Task 15)
- [ ] No approval HTTP JSON key changes
- [ ] No History/Compliance/HTML redesign
- [ ] Admin `#auditLog` shows server audit; download uses server data
- [ ] Command `#evidenceDetails` shows provenance meta
- [ ] Org/site change refreshes Admin audit
- [ ] `pytest -q backend/tests` passes
- [ ] `python -m compileall backend/app` passes
- [ ] `node --check` passes on modified JS files
- [ ] Manual validation steps in §9.4 completed
- [ ] Implementation report produced (files, APIs, UI, risks, testing)
- [ ] No autonomous execution or decision-making introduced

---

## Implementation sequence (mandatory order)

After this contract is approved:

0. Create checkpoint commit (current tree / branch baseline).
1. `backend/app/core/config.py`
2. `backend/app/security/authorization.py`
3. `backend/app/models.py`
4. `backend/app/schemas.py`
5. `backend/app/database.py` + `lifespan` in `main.py`
6. Create `backend/app/audit.py`
7. Instrument auth in `main.py`
8. Instrument approvals in `main.py`
9. Instrument incidents/events/evidence/report/seed in `main.py`
10. Add `GET /api/v1/audit` in `main.py`
11. Create `backend/tests/test_audit.py` (+ minimal `test_api.py` fix only if required)
12. `frontend/js/api.js`
13. `frontend/js/enterprise.js`, `incidents.js`, `app.js`
14. Run full test/verification plan
15. Produce implementation report

**Do not deviate from this specification without asking.**

---

## Document control

| Field | Value |
|-------|-------|
| Contract ID | TASK16_IMPLEMENTATION_SPEC |
| Path | `docs/design/TASK16_IMPLEMENTATION_SPEC.md` |
| Created for | APPLY_TASK_16 / Module 11 |
| Next gate | Human approval → checkpoint commit → implement exactly |
