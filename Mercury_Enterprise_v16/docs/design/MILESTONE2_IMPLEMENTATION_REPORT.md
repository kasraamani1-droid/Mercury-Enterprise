# Milestone 2 Implementation Report

**Milestone:** Milestone 2 — Explainability, Production Readiness, Release Candidate  
**Tasks:** 19 (AI Explainability & Decision Review), 20 (Production Observability, Resilience & Packaging)  
**Branch:** `task-16-audit-provenance`  
**Contract:** `docs/design/MILESTONE2_IMPLEMENTATION_SPEC.md`  
**Checkpoint:** `d77d78c` / tag `checkpoint-milestone-2-pre`  
**Final status:** **READY TO ACCEPT (engineering RC)**  
**Merge / push:** Not performed (per instruction)

---

## Commit timeline

| Commit | Description |
|--------|-------------|
| `c741e7f` | Milestone 1 completed (Tasks 16-18) — baseline |
| `d77d78c` | Milestone 2 approved-spec checkpoint (pre-implementation) |
| `b950481` | Module 14 — Task 19 AI Explainability and Decision Review |
| `f9d027c` | Module 15 — Task 20 Production Observability, Resilience, and Packaging |
| *(this report)* | Milestone 2 implementation report |

---

## Files changed

### Task 19
- `backend/app/decision/decision_engine.py` — store, review, connector context, enriched evaluate
- `backend/app/decision/explanations.py` — structured assumptions/uncertainty/factors/evidence links
- `backend/app/decision/models.py` — additive DecisionResult fields
- `backend/app/main.py` — `/decisions*` routes; dashboard decision enrichment; seed evidence backfill
- `backend/app/schemas.py` — `DecisionEvaluateRequest`, `DecisionReviewRequest`
- `backend/app/security/authorization.py` — `decisions.read`, `decisions.review`
- `backend/tests/test_decision_engine.py` — explanation + review unit coverage
- `backend/tests/test_decisions_api.py` — **created** API/RBAC/site/audit tests
- `frontend/index.html` — Decision Timeline explain/review DOM ids
- `frontend/js/api.js` — decision client helpers
- `frontend/js/app.js` — Command explain/alternatives/review UI

### Task 20
- `backend/app/core/health.py` — **created** shared health/ready/platform/ops builders
- `backend/app/core/logging.py` — optional JSON logging; retained text format
- `backend/app/core/config.py` — `log_json`, `metrics_enabled` (metrics default off)
- `backend/app/main.py` — enriched health/ready/platform; request logging
- `backend/app/routers/ops.py` — enriched `/ops/health`
- `backend/tests/test_observability.py` — **created**
- `docker-compose.yml` — backend `/ready` healthcheck
- `.github/workflows/ci.yml` — expanded JS checks + compose config (best-effort)
- `frontend/js/app.js` — degraded health status strip
- `docs/PRODUCTION_READINESS.md` — RC provided vs still-required
- `docs/FINAL_RELEASE_GUIDE.md` — RC smoke steps
- `docs/ARCHITECTURE.md` — Milestone 2 module notes
- `docs/runbooks/OPERATOR.md` — **created**
- `docs/runbooks/ADMINISTRATOR.md` — **created**
- `docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md` — **created**
- `docs/runbooks/DISASTER_RECOVERY.md` — **created**

### Docs (planning)
- `docs/design/MILESTONE2_IMPLEMENTATION_SPEC.md` — approved contract
- `docs/design/MILESTONE2_IMPLEMENTATION_REPORT.md` — this report

---

## APIs added

| Method | Path | Task | Auth |
|--------|------|------|------|
| `POST` | `/api/v1/decisions/evaluate` | 19 | `decisions.read` |
| `GET` | `/api/v1/decisions` | 19 | `decisions.read` |
| `GET` | `/api/v1/decisions/{decision_id}` | 19 | `decisions.read` |
| `POST` | `/api/v1/decisions/{decision_id}/review` | 19 | `decisions.review` |

## APIs modified (additive)

| Method | Path | Task | Change |
|--------|------|------|--------|
| `GET` | `/api/v1/dashboard/summary` | 19 | Additive decision keys + richer timeline items; optional session site scope |
| `GET` | `/api/v1/health` | 20 | connectors, decision_support, checks |
| `GET` | `/api/v1/ready` | 20 | checks; **503** when DB unavailable |
| `GET` | `/api/v1/platform/status` | 20 | real-er service signals + connectors |
| `GET` | `/api/v1/ops/health` | 20 | subsystem summary |

**Not added (per locked defaults):** `GET /api/v1/metrics`

---

## Database changes

| Change | Decision |
|--------|----------|
| New tables | **None** (Task 19 Option A; Task 20 none) |
| New columns | **None** |
| Durable attribution | Reused `audit_events` (`decision.evaluate`, `decision.review`) |
| In-memory | Bounded decision store (max 200) on `DecisionEngine` |

---

## Tests executed

| Suite | Result |
|-------|--------|
| `pytest -q backend/tests` | **69 passed** |
| `python -m compileall backend/app` | OK |
| `node --check frontend/js/api.js` | OK |
| `node --check frontend/js/app.js` | OK |
| `node --check frontend/js/enterprise.js` | OK |
| `node --check frontend/js/enterprise8.js` | OK |

### Coverage notes

- No separate coverage percentage tool was configured in-repo; validation is pytest suite completeness + syntax checks.
- New coverage areas: decision explanation payloads, review transitions, RBAC/site isolation, audit side-effects, health/ready degraded paths, ops/platform diagnostics, decision resilience under connector noise.
- Prior Milestone 1 suites (audit, reporting, connectors) remain green.

---

## Risks

| Risk | Status / mitigation |
|------|---------------------|
| Operators confuse review with execution authority | Advisory banner + `advisory_only` / `automatic_execution=false` + runbook language |
| Decision reviews lost on restart (Option A) | Documented; durable audit remains; Option B not enabled |
| Health endpoints must not leak secrets | Tests assert no password/secret strings; public probes redacted |
| Ready too strict on connectors | Ready depends on **DB only**; connectors reported as degraded counts |
| Nested package CI path | Workflow uses `working-directory: Mercury_Enterprise_v16` |
| Local `mercury.db` pollution | Seed backfill ensures seed evidence exists when missing |

---

## Remaining technical debt

1. Decision review durability across restarts (Option B table) — deferred unless required.
2. `/metrics` endpoint — deferred (default off).
3. Approvals are durable SQL (`approval_requests`; RC1 Blocker 03).
4. Connector health history remains in-memory ring (pre-existing).
5. `GET /incidents` still not globally site-filtered (pre-existing).
6. Some dashboard/category connector mappings remain partially synthetic.
7. No frontend e2e suite beyond `node --check`.
8. Demo credentials remain unsuitable for live production IdP integration.
9. GitHub Actions workflow lives under nested `Mercury_Enterprise_v16/.github` — confirm hosting root discovers it, or relocate later.
10. External certification / penetration / load / legal reviews remain outside RC.

---

## Acceptance summary

- Task 19: richer explainability + human review on existing DecisionEngine/Command surfaces — **done**
- Task 20: observability, resilience signaling, packaging validation hooks, runbooks — **done**
- Architecture constraints preserved (vanilla JS, FastAPI, additive, no duplicate platforms)
- Human-control / advisory invariants preserved
- Engineering RC documentation complete
- **No merge performed**

---

## Suggested next steps (human only)

1. Accept this report.
2. Optional: push branch / open PR.
3. Optional: tag `rc-mercury-enterprise-v2.0` after acceptance.
4. Do not merge until explicitly approved.
