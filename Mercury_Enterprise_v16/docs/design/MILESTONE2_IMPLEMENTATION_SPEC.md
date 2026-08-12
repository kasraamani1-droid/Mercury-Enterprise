# Milestone 2 Implementation Specification (Expanded)

**Milestone:** Milestone 2 — Explainability, Production Readiness, Release Candidate  
**Tasks:** 19 (AI Explainability & Decision Review), 20 (Production Observability, Resilience & Packaging)  
**Plus:** Final production readiness, remaining documentation, final regression testing, Release Candidate preparation  
**Status:** CONTRACT — await human approval before checkpoint / implementation  
**Architecture constraints:** Vanilla JavaScript frontend, FastAPI backend, additive changes only. No redesign. No duplicate platforms. Preserve Tasks 12–18 behavior and backward-compatible APIs.

**Baseline**
| Item | Value |
|------|-------|
| Branch | `task-16-audit-provenance` |
| Checkpoint | `c741e7f` — *Milestone 1 completed (Tasks 16-18)* |
| Prerequisite | Milestone 1 accepted (`docs/design/MILESTONE1_IMPLEMENTATION_REPORT.md`) |
| Related contracts | `APPLY_TASK_19.md`, `APPLY_TASK_20.md`, `docs/design/MILESTONE1_IMPLEMENTATION_SPEC.md` |
| Engineering gates | `docs/AI_ENGINEERING_WORKFLOW.md` |

**Do not implement until this contract is explicitly approved.**

---

## 0. Locked defaults (unless approval overrides)

| Decision | Default |
|----------|---------|
| Review durability | **Option A** — in-memory bounded decision store + durable `audit_events` for review actions. No `decision_reviews` SQL table unless you explicitly require restart-safe review continuity (Option B). |
| Metrics | **No `/metrics` in Task 20 by default** — enrich `/health`, `/ready`, `/platform/status`, and `/ops/health` first. Add `/metrics` only if RC diagnostics remain insufficient and you approve. |
| Evaluate context | Server enriches from MissionService / AlertManager / Fusion / ConnectorManager; client may supply `mission_id`, `track_id`, `threat_score` or `threat_level` (validated by `DecisionEngine.validate_context`). |
| `/ops/coordinate` | **Unchanged** — remains ResponseOrchestrationEngine path; not the DecisionEngine explain/review surface. |

---

## 1. Architecture (unchanged principles)

```text
Frontend (vanilla JS shells only)
  Command explain/review · History optional · Admin diagnostics · Integrations (T18)
        │ /api/v1/* session + RBAC + site
FastAPI
  T13–T18 foundations · DecisionEngine (T19) · health/logging/packaging (T20)
        │
Persistence: existing SQL + audit_events · in-memory decisions (Option A)
Packaging: docker-compose · Dockerfiles · nginx · CI · docs/runbooks
```

**Non-negotiable:** one DecisionEngine; advisory-only; human review; audit continuity; no second AI/review/dashboard/deployment stack; no React/Vue/Angular/Next; no Alembic unless separately approved.

---

## 2. Dependency graph — implementation order

### 2.1 Milestone-level order (hard)

```text
c741e7f (M1 complete)
    │
    ▼
[APPROVAL] MILESTONE2_IMPLEMENTATION_SPEC.md
    │
    ▼
P1 Checkpoint: tag checkpoint-milestone-2-pre
    │
    ▼
╔══════════════════════════════════════════════════════════════╗
║  TASK 19 — Module 14 (must finish + green before Task 20)    ║
╚══════════════════════════════════════════════════════════════╝
    │
    ▼
╔══════════════════════════════════════════════════════════════╗
║  TASK 20 — Module 15                                         ║
╚══════════════════════════════════════════════════════════════╝
    │
    ▼
RC: final regression → MILESTONE2_IMPLEMENTATION_REPORT.md
    → checklist → stop for release/merge approval
```

### 2.2 Task 19 internal dependency graph (strict sequence)

```text
T19.1  authorization.py permissions
         │
T19.2  decision/models.py additive fields
         │
T19.3  decision/explanations.py richer explain
         │
T19.4  decision/decision_engine.py wire explain + review helpers + store
         │
T19.5  schemas.py request/response models
         │
T19.6  main.py routes + dashboard/summary enrichment + audit side-effects
         │  (uses: DecisionEngine, record_audit, require_session/permissions,
         │   connector_manager for connector_context, session org/site)
         │
T19.7  backend/tests (engine + API) ── must pass ──┐
                                                   │
T19.8  frontend/js/api.js                          │
         │                                         │
T19.9  frontend/index.html minimal DOM ids         │
         │                                         │
T19.10 frontend/js/app.js Command UI               │
         │                                         │
T19.11 frontend/js/enterprise.js (optional History)│
         │                                         │
T19.12 node --check + manual smoke ←───────────────┘
         │
T19.13 Commit: Module 14 - AI Explainability and Decision Review
```

**Do not** start frontend until T19.6–T19.7 are green.  
**Do not** open Task 20 files for feature work during Task 19 (docs-only notes allowed).

### 2.3 Task 20 internal dependency graph (strict sequence)

```text
T20.0  Re-run full pytest (T12–T19 baseline) — must be green
         │
T20.1  config.py + logging.py (+ request_context in main.py)
         │
T20.2  health / ready / platform/status / ops/health enrichment
         │
T20.3  resilience hardening (safe errors; ready=false on DB fail)
         │
T20.4  backend/tests/test_observability.py (or extend test_api)
         │
T20.5  packaging: compose/nginx/CI only if validation finds gaps
         │
T20.6  frontend diagnostics bind (app.js / enterprise.js minimal)
         │
T20.7  docs/runbooks/* + PRODUCTION_READINESS + FINAL_RELEASE_GUIDE
         │   + ARCHITECTURE touch-up
         │
T20.8  packaging/docs verification + full regression
         │
T20.9  Commit: Module 15 - Production Observability, Resilience, and Packaging
         │
T20.10 RC report + checklist (separate commit ok)
```

### 2.4 Cross-task dependency matrix

| Work item | Depends on | Blocks |
|-----------|------------|--------|
| T19 evaluate API | DecisionEngine, session, `decisions.read` | Command explain UI |
| T19 review API | evaluate store, `decisions.review`, `record_audit` | Review UI, audit proof |
| T19 connector_context | ConnectorManager (T18) | Trust warnings in UI |
| T19 dashboard additive keys | evaluate/store or timeline | Command widgets |
| T20 health enrichment | T19 complete (regression baseline) | Runbooks, RC |
| T20 runbooks | Actual T19/T20 endpoints | RC sign-off |
| RC report | T19+T20 commits green | Merge/tag approval |

### 2.5 Forbidden parallelization

- Implementing T20 metrics/runbooks before T19 acceptance  
- Creating `decision_reviews` table without Option B approval  
- Adding `/metrics` without metrics approval  
- Touching `/incidents/{id}/assessment` as a DecisionEngine replacement  
- New workspace tabs or second frontend apps  

---

# TASK 19 — AI Explainability and Decision Review (Module 14)

## T19.1 Exact files to modify

| Path | Action | Exact responsibility |
|------|--------|----------------------|
| `backend/app/security/authorization.py` | **Modify** | Add `decisions.read`, `decisions.review` to `PERMISSIONS_BY_ROLE` |
| `backend/app/decision/models.py` | **Modify** | Additive fields on `DecisionResult` / `to_dict()`: `assumptions`, `uncertainty`, `factor_breakdown`, `evidence_links`, `connector_context`, `review`, `disclaimer`; keep existing keys |
| `backend/app/decision/explanations.py` | **Modify** | Extend `DecisionExplanationEngine.explain` to return structured assumptions, uncertainty, factor breakdown (not only narrative string) |
| `backend/app/decision/decision_engine.py` | **Modify** | Wire enriched explain; stamp org/site from context; attach connector_context; maintain in-memory store; `apply_review()` helper; force advisory metadata |
| `backend/app/decision/__init__.py` | **Modify only if** exports needed | Keep public exports stable |
| `backend/app/schemas.py` | **Modify** | `DecisionEvaluateRequest`, `DecisionReviewRequest`, response models / TypedDicts as used by FastAPI |
| `backend/app/main.py` | **Modify** | Wire `POST/GET /decisions*`; enrich `dashboard_summary` decisions + `decision_timeline`; call `record_audit` |
| `backend/app/audit.py` | **Reuse only** | No API change required; call existing `record_audit` |
| `backend/app/connectors/manager.py` | **Reuse only** | `list_records()` / health for `connector_context` |
| `backend/tests/test_decision_engine.py` | **Modify** | Explanation richness + advisory invariants |
| `backend/tests/test_decisions_api.py` | **Create** | HTTP RBAC/site/review/audit tests |
| `backend/tests/conftest.py` | **Modify if needed** | Auth helpers / session fixtures for decision roles |
| `frontend/js/api.js` | **Modify** | `evaluateDecision`, `listDecisions`, `getDecision`, `reviewDecision` |
| `frontend/js/app.js` | **Modify** | `renderDashboardSummary` decision section; explain/alternatives/review UI; evaluate/review actions |
| `frontend/index.html` | **Modify (minimal)** | Add DOM containers listed in T19.4 under existing Decision Timeline article — no new workspace |
| `frontend/js/enterprise.js` | **Modify (optional)** | If History shows decision-review audit/history rows; prefer audit/reports reuse |
| `frontend/js/assessment.js` | **Do not modify by default** | Keep assessment separate; optional one-line advisory disclaimer only if needed |

**Do not create:** `ExplainabilityManager`, `AIReviewService`, `backend/app/decision_review/`, new workspace HTML sections, React components.

**Option B only (not default):** also modify `backend/app/models.py`, `backend/app/database.py` for `decision_reviews` table + `ensure_schema()`.

---

## T19.2 Exact APIs to add or modify

### Modify (additive)

| Method | Path | Change |
|--------|------|--------|
| `GET` | `/api/v1/dashboard/summary` | Extend `decisions` object and `decision_timeline` items; **preserve all existing keys** |

**Additive `decisions` keys (exact contract):**
- `pending_human_review` (existing — prefer count of review.state=`pending` when store available, else timeline fallback)
- `highest_threat_level` (existing)
- `selected_recommendation` (existing — populate from latest site-scoped decision when available)
- `status` (existing)
- **New:** `warning_count` (int)
- **New:** `alternative_count` (int)
- **New:** `latest_decision_id` (str \| null)
- **New:** `latest_review_state` (str \| null)
- **New:** `advisory_only` (bool, always `true`)

**Additive `decision_timeline[]` item keys:**
- Keep: `timestamp`, `decision`, `operator_acknowledged`
- **New:** `decision_id` (str \| null)
- **New:** `review_state` (str \| null)
- **New:** `selected_name` (str \| null)
- **New:** `warning_count` (int, default 0)
- Set `operator_acknowledged` from review state ∈ `{acknowledged, commented}` (not hardcoded `false`)

### Add (minimal `/api/v1/decisions` family)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/v1/decisions/evaluate` | session + `decisions.read` | Run `decision_engine.evaluate`; stamp org/site; store; audit `decision.evaluate`; return full payload |
| `GET` | `/api/v1/decisions` | session + `decisions.read` | List recent site-scoped decisions (`limit` default 20, max 100) |
| `GET` | `/api/v1/decisions/{decision_id}` | session + `decisions.read` | Get one decision + review; 404 if missing or wrong site |
| `POST` | `/api/v1/decisions/{decision_id}/review` | session + `decisions.review` | Apply review transition + comment; audit `decision.review` |

### Unchanged (must not break)

| Method | Path | Note |
|--------|------|------|
| `GET` | `/api/v1/incidents/{id}/assessment` | Separate assessment engine |
| `POST` | `/api/v1/ops/coordinate` | Orchestration, not DecisionEngine review |
| `GET` | `/api/v1/reports/*` | Compatible; may later count decision audit actions — no contract break |
| `GET` | `/api/v1/audit` | Review actions appear as audit rows |

### Request/response contracts

**`POST /decisions/evaluate` body (exact fields allowed):**
```json
{
  "mission_id": "string (required by engine)",
  "track_id": "string (required by engine)",
  "threat_level": "string (optional if threat_score provided)",
  "threat_score": "number (optional if threat_level provided)",
  "active_alerts": "bool or list (optional)",
  "operator_constraints": "list[str] (optional)",
  "response_recommendations": "list (optional — engine may use/fallback)"
}
```
Server **overwrites** `organization_id` / `site_id` from session. Client cannot widen scope.

**Response:** existing `DecisionResult.to_dict()` plus:
```json
{
  "assumptions": ["string"],
  "uncertainty": ["string"],
  "factor_breakdown": [{"name": "string", "weight_or_score": 0.0, "detail": "string"}],
  "evidence_links": [{"label": "string", "ref": "string"}],
  "connector_context": {"degraded": ["id"], "error": ["id"], "online": 0, "total": 0},
  "organization_id": "string",
  "site_id": "string",
  "review": {
    "state": "pending",
    "comment": null,
    "reviewed_by": null,
    "reviewed_at": null
  },
  "disclaimer": "Advisory decision support only. Human operator remains in full control.",
  "metadata": {
    "automatic_execution": false,
    "advisory_only": true,
    "source": "decision_engine"
  }
}
```

**`POST /decisions/{id}/review` body:**
```json
{
  "state": "acknowledged | commented | rejected_advisory",
  "comment": "string (optional; required if state=commented)"
}
```

**Allowed transitions (exact):**
| From | To | Notes |
|------|----|-------|
| `pending` | `acknowledged` | Human ack; comment optional |
| `pending` | `commented` | Comment required |
| `pending` | `rejected_advisory` | Reject recommendation as advisory only — **does not** execute alternative |
| `commented` | `acknowledged` | Allowed |
| `acknowledged` / `rejected_advisory` | * | **409** — terminal for RC (no reopen unless approved later) |

**Errors:** `401`, `403`, `404`, `409` (invalid transition), `422` (invalid context / missing comment).

### RBAC mapping (exact)

| Permission | Viewer | Operator | Reviewer | Administrator |
|------------|--------|----------|----------|---------------|
| `decisions.read` | ✓ | ✓ | ✓ | `*` |
| `decisions.review` | ✗ | ✓ | ✓ | `*` |

---

## T19.3 Exact database changes

| Change | Decision |
|--------|----------|
| New SQL tables | **None (Option A default)** |
| New columns on existing tables | **None** |
| Durable attribution | Reuse `audit_events` via `record_audit` with actions `decision.evaluate`, `decision.review` |
| In-memory store | Module-level or `app.state` bounded dict/ring (max **200** decision payloads per process), keyed by `decision_id`, filtered by org/site |

**Option B (only if approved):** table `decision_reviews` with columns `id`, `decision_id` (unique), `organization_id`, `site_id`, `payload_json`, `review_state`, `review_comment`, `reviewed_by`, `created_at`, `updated_at`; created in `ensure_schema()` / `models.py`; no Alembic.

---

## T19.4 Exact frontend components

Mercury has **no React components**. “Components” = existing DOM regions + JS render functions.

### Reuse / bind (existing)

| DOM id / region | File | Change |
|-----------------|------|--------|
| `#decisionTimelineList` | `index.html` + `app.js` `renderDashboardSummary` | Richer rows; click selects decision detail |
| `#dashboardPendingDecisions` | existing | Bind pending review count from enriched summary |
| `#dashboardDecisionDot` / `#dashboardDecisionStatus` | existing | Reflect review/advisory status |
| `#dashboardHighestThreat` | existing | Unchanged binding |
| `#dashboardSummaryMessage` | existing | Include selected recommendation + advisory wording |
| `#assessmentTab` | `assessment.js` | **No DecisionEngine takeover** |

### Add (minimal DOM — inside existing Decision Timeline article only)

| New DOM id | Purpose |
|------------|---------|
| `#decisionExplainPanel` | Container for selected decision explanation |
| `#decisionAlternativesList` | Ranked alternatives comparison |
| `#decisionFactorsList` | Factor breakdown / constraints / warnings / assumptions / uncertainty |
| `#decisionReviewState` | Current review state label |
| `#decisionReviewComment` | Comment textarea (review roles) |
| `#decisionReviewSubmit` | Submit review button |
| `#decisionEvaluateButton` | Optional explicit evaluate trigger (Operator/Viewer with read) |
| `#decisionAdvisoryBanner` | Static/advisory-only banner text |

**Layout rule:** place these under the existing “Decision Timeline” `article.card.dashboard-summary` (after `#decisionTimelineList`). Do **not** add a new workspace, tab, or Intelligence tab.

### JS functions (exact intent)

| Function | File | Role |
|----------|------|------|
| `renderDashboardSummary` | `app.js` | Extend decision timeline rendering |
| `renderDecisionExplain(decision)` | `app.js` **new function** | Fill explain/alternatives/factors/review panel |
| `submitDecisionReview()` | `app.js` **new function** | Call review API; refresh summary |
| `evaluateDecisionFromUi()` | `app.js` **new function** | Build minimal context from session/mission fields; call evaluate |
| `evaluateDecision` / `listDecisions` / `getDecision` / `reviewDecision` | `api.js` **new exports** | Thin fetch wrappers |

---

## T19.5 Reused code

| Symbol / module | Path | Reuse how |
|-----------------|------|-----------|
| `DecisionEngine` | `decision/decision_engine.py` | Sole evaluation path |
| `DecisionScoringEngine` | `decision/scoring.py` | Unchanged scoring weights unless bugfix required |
| `DecisionExplanationEngine` | `decision/explanations.py` | Extend, do not replace |
| `DecisionCandidate` / `DecisionResult` | `decision/models.py` | Additive fields |
| `ThreatRiskEngine` | `ai/` | Existing recommendation fallback inside engine |
| `MissionService`, `AlertManager`, `FusionEngine`, `TimelineManager`, `EventBus` | existing | Context enrichment / events |
| `ConnectorManager.list_records` | `connectors/manager.py` | `connector_context` |
| `record_audit` / `list_audit_events` | `audit.py` | Review/evaluate attribution |
| `require_session` / `require_permissions` | `main.py` / `authorization.py` | Gate routes |
| Session org/site | Task 15 context | Force stamp + filter |
| `getDashboardSummary` pattern | `api.js` / `app.js` | Extend Command binding |
| Alert ack UX pattern | alerts ack | Model review button UX lightly |

---

## T19.6 New code

| New unit | Kind | Notes |
|----------|------|-------|
| In-memory `_decision_store` (name flexible) | New helper in `decision_engine.py` or small `decision/store.py` | Bounded ring; **not** a second platform |
| `apply_review(decision_id, state, comment, actor, org, site)` | New method | Transition + mutate store |
| `build_connector_context(connector_manager)` | New helper | Degraded/error lists |
| `DecisionEvaluateRequest` / `DecisionReviewRequest` | New schemas | Validation only |
| Four `/decisions*` route handlers | New in `main.py` | No new router package required (keep in `main.py` for consistency with audit/reports) **or** `routers/decisions.py` only if `main.py` size becomes unsafe — prefer `main.py` first |
| `test_decisions_api.py` | New test module | API contract |
| Frontend API exports + render helpers | New functions | No new JS framework files |

**Forbidden new code:** second engine, vector DB, model registry, autonomous executor, duplicate History workspace.

---

## T19.7 Testing plan

### Automated

| Test | Location | Assert |
|------|----------|--------|
| Enriched explain fields present | `test_decision_engine.py` | `assumptions`, `uncertainty`, `factor_breakdown`, `warnings` keys; lists (may be empty) |
| Alternatives ranked | `test_decision_engine.py` | `ranked_actions` sorted by `overall_score` desc; selected == top |
| Advisory invariants | `test_decision_engine.py` | `requires_human_approval is True`; `metadata.automatic_execution is False`; `advisory_only is True` |
| Evaluate API 200 | `test_decisions_api.py` | Payload shape; org/site stamped from session |
| Evaluate RBAC | `test_decisions_api.py` | Unauth 401; missing perm 403 |
| List/get site isolation | `test_decisions_api.py` | Cross-site get → 404/empty |
| Review happy path | `test_decisions_api.py` | pending→acknowledged; audit row `decision.review` |
| Review invalid transition | `test_decisions_api.py` | 409 |
| Review comment required | `test_decisions_api.py` | commented without comment → 422 |
| Viewer cannot review | `test_decisions_api.py` | 403 |
| Dashboard additive keys | `test_decisions_api.py` or `test_api.py` | Existing keys still present + new keys |
| Regression | full suite | `test_audit`, `test_reporting`, `test_connectors` pass |

### Frontend checks

- `node --check frontend/js/api.js`
- `node --check frontend/js/app.js`
- `node --check frontend/js/enterprise.js` if touched

### Manual smoke

1. Login as Operator → evaluate → see alternatives/factors/warnings  
2. Submit review comment/ack → timeline shows acknowledged  
3. Login as Viewer → can read, cannot submit review  
4. Login as Reviewer → can review  
5. Admin `#auditLog` shows `decision.evaluate` / `decision.review`  
6. Confirm UI copy remains advisory; Actions tab buttons do not auto-fire from review  

### Exit criteria for Task 19

`pytest -q backend/tests` green + node checks + manual smoke signed in notes → then commit Module 14.

---

## T19.8 Rollback plan

| Layer | Action |
|-------|--------|
| Git | `git revert` Module 14 commit or reset soft to `checkpoint-milestone-2-pre` / `c741e7f` (only with approval for hard reset) |
| API | Removing routes is safe (additive); old clients ignore missing `/decisions` |
| Dashboard | Additive keys — old frontend ignores unknown keys; reverted frontend ignores new backend keys |
| Memory store | Cleared on process restart; no migration |
| Audit rows | **Retain** — do not delete `decision.*` audit events on rollback |
| Option B | Leave unused table; do not DROP in emergency without backup |

---

## T19.9 Performance considerations

| Topic | Constraint |
|-------|------------|
| Evaluate latency | Target &lt; 200ms CPU for demo contexts; avoid remote calls in explain path |
| Decision store | Cap **200** entries; evict oldest; O(1) get by id |
| Dashboard summary | Do not call full evaluate on every summary poll; read from store/timeline only |
| List endpoint | Default limit 20; hard max 100 |
| Connector context | Use in-memory `list_records()` only — no per-connector poll inside evaluate |
| Scoring | Keep deterministic in-process scoring; no new ML inference runtime |
| Frontend | Render selected decision detail on demand (click), not all alternatives DOM for every timeline row |

---

## T19.10 Security considerations

| Topic | Requirement |
|-------|-------------|
| Authn | All `/decisions*` require session cookie |
| Authz | `decisions.read` / `decisions.review` enforced |
| Site scope | Force org/site from session; never trust client org/site |
| Advisory safety | Review never triggers mission execution, targeting, weapons, or connector recover |
| Injection | Treat comments as plain text; escape in DOM (`textContent` / existing safe patterns) |
| Secrets | Never put passwords/API keys in decision payload or audit details |
| Assessment isolation | Do not merge assessment API auth gaps into DecisionEngine blindly |
| Audit integrity | Evaluate + review always `record_audit` with actor + site |

---

## T19.11 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Operators confuse review with authorization to act | Med | High | Persistent advisory banner; `rejected_advisory` naming; tests for no auto-exec |
| In-memory loss on restart | Med | Med | Documented Option A; audit remains; Option B if required |
| Dashboard poll overload if evaluate hooked wrongly | Med | Med | Summary reads store only |
| Duplicate “AI” UX vs assessment tab | Med | Low | Keep assessment separate; clear labels |
| `main.py` growth | Med | Low | Prefer keep routes in main; extract router only if necessary |
| Over-rich explain inventing fake evidence | Med | Med | `evidence_links` only from real context refs; empty list OK |
| RBAC mis-assign Viewer review | Low | High | Explicit matrix + tests |

---

## T19.12 Acceptance criteria

- [ ] Task 12 Command shell intact (no new workspace)  
- [ ] Tasks 13–18 session/RBAC/site/audit/reports/connectors behaviors still pass tests  
- [ ] `POST /api/v1/decisions/evaluate` returns richer explanation + `ranked_actions`  
- [ ] Alternatives, factors, warnings, assumptions, uncertainty visible in Command  
- [ ] Review states work with RBAC + site scope + audit  
- [ ] `requires_human_approval=true`, `automatic_execution=false`, advisory disclaimer present  
- [ ] `GET /dashboard/summary` additive-compatible  
- [ ] No second AI/decision/review platform or duplicate API family  
- [ ] Option A: no new DB tables (unless Option B approved)  
- [ ] Commit message: `Module 14 - AI Explainability and Decision Review`  

---

# TASK 20 — Production Observability, Resilience, and Packaging (Module 15)

## T20.1 Exact files to modify

| Path | Action | Exact responsibility |
|------|--------|----------------------|
| `backend/app/core/config.py` | **Modify** | Optional flags: `log_json` / `metrics_enabled` (default false) / document env vars; no behavior break |
| `backend/app/core/logging.py` | **Modify** | Richer format including level/name; optional JSON formatter behind env |
| `backend/app/main.py` | **Modify** | Enrich `health`, `ready`, `platform_status`; improve `request_context` logging (status, path, request id, latency — already partially present); **do not** break existing response shapes beyond additive keys |
| `backend/app/routers/ops.py` | **Modify** | Enrich `GET /api/v1/ops/health` with safe subsystem summary (DB ping optional, connector counts, advisory mode flag) |
| `backend/tests/test_observability.py` | **Create** | Health/ready/platform/ops health tests |
| `backend/tests/test_api.py` | **Modify if needed** | Compatibility asserts for additive health keys |
| `frontend/js/api.js` | **Modify** | Optional `getReady`, `getPlatformStatus`, `getOpsHealth` helpers if UI binds them |
| `frontend/js/app.js` | **Modify** | Bind degraded/ready messaging into existing `#statusText` / `#dashboardPlatformStatus` without new dashboard |
| `frontend/js/enterprise.js` | **Modify if needed** | Admin-facing status text only if an existing admin node exists |
| `frontend/js/enterprise8.js` | **Touch only if** degraded copy consistency needed | Prefer no change |
| `docker-compose.yml` | **Modify only if** validation gap | Healthcheck alignment with `/ready` |
| `docker-compose.dev.yml` | **Modify only if** needed | Same |
| `backend/Dockerfile` / `frontend/Dockerfile` | **Modify only if** needed | Packaging fixes |
| `frontend/nginx.conf` | **Modify only if** needed | Preserve `X-Request-ID` proxy behavior |
| `deploy/nginx-production.conf` | **Modify only if** needed | Doc-aligned TLS sketch; no redesign |
| `.github/workflows/ci.yml` | **Modify** | Add `node --check` for all touched JS files; optional `docker compose config` |
| `docs/PRODUCTION_READINESS.md` | **Modify** | Split “provided in RC” vs “still required before live ops” |
| `docs/FINAL_RELEASE_GUIDE.md` | **Modify** | RC verify steps including health/ready and decision review |
| `docs/ARCHITECTURE.md` | **Modify** | Note T19/T20 extensions |
| `docs/runbooks/OPERATOR.md` | **Create** | Normal ops, degraded mode, alert triage, decision review |
| `docs/runbooks/ADMINISTRATOR.md` | **Create** | Deploy, health, connectors, users/roles, audit |
| `docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md` | **Create** | Upgrade/rollback procedures |
| `docs/runbooks/DISASTER_RECOVERY.md` | **Create** | Backup/restore expectations for SQLite/Postgres compose volumes |
| `docs/design/MILESTONE2_IMPLEMENTATION_REPORT.md` | **Create** (end) | Evidence |
| `docs/decisions/ADR-001-*.md` | **Create only if** Option B or `/metrics` approved | |

**Do not create:** second compose stack, Kubernetes operator, Prometheus/Grafana requirement, new APM service, new admin SPA.

---

## T20.2 Exact APIs to add or modify

### Modify (additive)

| Method | Path | Auth | Exact change |
|--------|------|------|--------------|
| `GET` | `/api/v1/health` | open | Keep `status`, `version`, `environment`, `database`, `simulated`. **Add:** `request_id` optional N/A; `connectors` summary `{online, degraded, error, offline, total}`; `decision_support` `{advisory_only: true}`; `checks` `{database: "ok\|error"}` |
| `GET` | `/api/v1/ready` | open | Keep `ready`, `version`. On DB failure: HTTP **503** with `{"ready": false, "reason": "database"}` (or FastAPI HTTPException). **Add:** `checks` object |
| `GET` | `/api/v1/platform/status` | open/session as today | Replace purely hard-coded service map with **best-effort real signals**: api online, database from ping, events=`in-process`, ai=`decision_engine_advisory`. Keep `simulated` flag. Additive `connectors` aggregate optional |
| `GET` | `/api/v1/ops/health` | as today (open on router) | Expand beyond `{"status":"ok"}` to include `status`, `version`, `database`, `connectors`, `advisory_only: true` — still not a second health product |

### Add (optional — **not default**)

| Method | Path | Auth | When |
|--------|------|------|------|
| `GET` | `/api/v1/metrics` | session + Administrator (or `*` / explicit Operator if approved) | Only if approved; JSON counters: `http_requests`, `http_errors`, `decisions_evaluated`, `decisions_reviewed`, `connectors_by_state` |

### Unchanged

All T13–T19 business APIs; connector lifecycle; audit; reports; decisions.

### Resilience-related API behavior (exact)

| Condition | Behavior |
|-----------|----------|
| DB down | `/ready` → not ready (503); `/health` may report `database: "error"` / `status: "degraded"` |
| Connector degraded | APIs continue; health shows degraded counts; **no** auto mission/decision execution |
| Decision store empty after restart | `/decisions` empty; audit history still via `/audit`; UI shows empty-state, not crash |
| Unauthorized metrics (if enabled) | 401/403 |

---

## T20.3 Exact database changes

| Change | Decision |
|--------|----------|
| New tables | **None** |
| New columns | **None** |
| Migrations | **None** |
| Metrics persistence | In-process counters only (if metrics enabled) |
| DR | Document backup of SQLite file / Postgres volume — no new backup daemon required for RC |

---

## T20.4 Exact frontend components

| DOM / function | File | Change |
|----------------|------|--------|
| `#statusText` / `#backendDot` | `app.js` `checkHealth` | Prefer `/health` enriched status; show degraded if database/connectors degraded |
| `#dashboardPlatformStatus` | `app.js` `renderDashboardSummary` | Reflect platform/ready semantics already in summary where possible |
| `#connectorStatusLabel` / connector ids | existing T18 | Ensure labels consistent with runbook “degraded mode” language |
| Admin `#auditLog` | `enterprise.js` | No redesign; verify still loads (regression) |
| New DOM | **None required** | Prefer reuse strip/status nodes; add at most `#platformReadyBadge` if unavoidable — ask before adding |

**Do not** create a Monitoring workspace or metrics dashboard page.

---

## T20.5 Reused code

| Symbol / module | Path | Reuse how |
|-----------------|------|-----------|
| `health` / `ready` handlers | `main.py` | Extend in place |
| `request_context` middleware | `main.py` | Log status/latency/request id |
| `configure_logging` | `core/logging.py` | Extend |
| `settings` | `core/config.py` | Env-driven toggles |
| `ops_health` | `routers/ops.py` | Extend |
| `ConnectorManager` | connectors | Aggregate states for health |
| `decision_engine` / advisory flags | Task 19 | Surface `advisory_only` in health |
| Docker Compose / Dockerfiles / nginx | repo root | Validate/fix, don’t replace |
| CI workflow | `.github/workflows/ci.yml` | Extend steps |
| Existing docs structure | `docs/` | Expand production docs + new runbooks folder |

---

## T20.6 New code

| New unit | Kind | Notes |
|----------|------|-------|
| Health check helper(s) | Small functions in `main.py` or `core/health.py` | Shared by `/health`, `/ready`, `/ops/health` — **one** helper module max; not a new platform |
| In-process counters | Optional | Only if `/metrics` approved |
| `test_observability.py` | New tests | Required |
| `docs/runbooks/*.md` (4 files) | New docs | Required |
| `MILESTONE2_IMPLEMENTATION_REPORT.md` | New doc | End of milestone |

---

## T20.7 Testing plan

### Automated

| Test | Assert |
|------|--------|
| Health 200 shape | Required keys present; additive keys present; no secrets |
| Ready 200 when DB ok | `ready: true` |
| Ready fails when DB unavailable | Simulate engine dispose / bad URL in test; expect not ready |
| Platform status | Includes non-empty services; `ai` indicates advisory/rule engine |
| Ops health | status ok + additive subsystem fields |
| Metrics (if built) | Authz enforced; counters monotonic in-process |
| Decision evaluate still works when one connector degraded | 200 + connector_context non-fatal |
| Full regression | Entire `backend/tests` green |
| CI | pytest, compileall, expanded `node --check` |
| Compose | `docker compose config` succeeds (when Docker available) |

### Manual / packaging

1. Start via documented script or compose  
2. Hit `/api/v1/health` and `/api/v1/ready`  
3. Stop DB / break DSN → ready fails; UI shows backend issue without JS crash  
4. Connector stop → Integrations + health show degraded; Command still usable  
5. Walk OPERATOR + ADMINISTRATOR runbooks against live system  
6. Dry-run rollback steps from `DEPLOY_UPGRADE_ROLLBACK.md` on paper  

### Exit criteria for Task 20

Tests green + runbooks verified + PRODUCTION_READINESS updated → commit Module 15 → RC report.

---

## T20.8 Rollback plan

| Layer | Action |
|-------|--------|
| Git | Revert Module 15 commit; remain on Task 19 commit if needed |
| Health API | Additive keys — old probes ignore extras; reverting code restores prior JSON |
| Compose/nginx/CI | Revert files; redeploy previous images/tags |
| Docs | Revert docs commit; operational procedures fall back to prior FINAL_RELEASE_GUIDE |
| Data | No schema changes — no DB rollback |
| Counters | Memory only — cleared on restart |

**Never** wipe Postgres/SQLite volumes as a “rollback” unless performing an explicit DR drill with backup.

---

## T20.9 Performance considerations

| Topic | Constraint |
|-------|------------|
| Health/ready | Must stay cheap: one `SELECT 1`, in-memory connector counts — target &lt; 50ms local |
| No health storm | Do not poll every connector provider inside `/health` |
| Logging | Avoid logging full decision payloads at INFO; use DEBUG for bulky bodies |
| Metrics (optional) | Lock-free or light locking counters; never sync to DB per request |
| CI time | Keep suite fast; compose up-full not required in CI — `compose config` enough |
| Frontend | Health check interval unchanged unless proven noisy |

---

## T20.10 Security considerations

| Topic | Requirement |
|-------|-------------|
| Health surface | Public `/health` `/ready` must not leak secrets, session tokens, passwords, internal file paths, or raw connection strings |
| Ops/platform | Same redaction rules |
| Metrics (if any) | Authenticated + role-gated |
| Logging | No credential logging; redact Authorization/cookie headers |
| Hardening ≠ autonomy | Resilience features must not auto-approve decisions or auto-recover missions |
| RBAC under degrade | Session/RBAC/site checks remain mandatory when API is up |
| Cookie secure flag | Document `MERCURY_SESSION_COOKIE_SECURE` for production TLS deployments |
| Docs honesty | RC is reference-platform ready, not certified for live weapons/safety ops |

---

## T20.11 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Overstating “production ready” | Med | High | Split checklist: provided vs still-required |
| Duplicate health endpoints diverge | Med | Med | Shared helper for health payloads |
| Ready too strict (connectors) | Med | Med | Ready depends on **DB only** by default; connectors reported as degraded, not ready-fail |
| Runbooks drift from code | Med | High | Verify procedures during T20.8 before commit |
| CI `node --check` only on `app.js` today | High | Low | Expand CI file list |
| Docker unavailable on dev machine | Med | Low | Make compose validation best-effort; document skip |
| Scope creep into full APM/K8s | Med | High | Explicit non-goals; stop and ask |

---

## T20.12 Acceptance criteria

- [ ] Tasks 12–19 remain green under full pytest  
- [ ] `/health` and `/ready` enriched and tested; ready fails on DB loss  
- [ ] `/platform/status` and `/ops/health` reflect real-er signals without a second monitoring product  
- [ ] No new DB schema  
- [ ] Runbooks exist and match implemented commands/endpoints  
- [ ] `PRODUCTION_READINESS.md` distinguishes RC-provided vs still-required  
- [ ] CI/packaging extended appropriately  
- [ ] Human-control / advisory model unchanged  
- [ ] No duplicate deployment/frontend/reporting/audit systems  
- [ ] Commit: `Module 15 - Production Observability, Resilience, and Packaging`  
- [ ] RC: `MILESTONE2_IMPLEMENTATION_REPORT.md` + release checklist complete  

---

# RC preparation (after Task 20)

## RC regression gate

1. `pytest -q backend/tests`  
2. `python -m compileall backend/app`  
3. `node --check` on `frontend/js/api.js`, `app.js`, `enterprise.js`, `enterprise8.js`, and any other touched JS  
4. Manual smoke: login → evaluate/review → audit → reports → connectors → health/ready  
5. `docker compose config` when Docker available  

## RC deliverables

| Item | Path |
|------|------|
| Report | `docs/design/MILESTONE2_IMPLEMENTATION_REPORT.md` |
| Tag (after approval) | `rc-mercury-enterprise-v2.0` |
| Rollback reference | `docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md` |

## RC checklist

- [ ] Spec approved; checkpoint `checkpoint-milestone-2-pre` exists  
- [ ] Module 14 committed  
- [ ] Module 15 committed  
- [ ] Final regression green  
- [ ] Runbooks verified  
- [ ] Report written  
- [ ] No merge/push without explicit human approval  

---

## Open decisions (confirm at approval)

1. Review durability: **Option A (default)** vs Option B table?  
2. Add **`GET /api/v1/metrics`**? **Default no.**  
3. Extract `routers/decisions.py` vs keep routes in `main.py`? **Default keep in `main.py`.**  

---

**STOP — awaiting approval. Do not implement until approved.**
