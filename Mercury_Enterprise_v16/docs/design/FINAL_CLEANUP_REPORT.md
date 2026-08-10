# Final Cleanup Report

**Date:** 2026-08-10  
**Source:** `docs/design/FINAL_RELEASE_AUDIT.md` (cleanup-only scope)  
**Branch:** `task-16-audit-provenance`  
**Constraint:** No new product functionality — dead/duplicate removal, docs/typing/naming/imports/tests only  

---

## Summary

Cleanup addressed audit items that do **not** require new features (authz gates, API base URL changes, multi-worker sessions, CI relocation remain deferred as P0 product/hardening work).

**Tests:** `pytest -q backend/tests` → **70 passed**  
**Also:** `compileall backend/app`; `node --check` on `utils.js`, `app.js`, `enterprise.js`, `enterprise8.js`

---

## Files changed

### Removed (dead / junk)
| Path | Reason |
|------|--------|
| `backend/app/security/api_key.py` | Unused route guard; never wired |
| `tmp_models.txt` | Scratch junk |
| `tmp_schemas.txt` | Scratch junk |

### Backend
| Path | Change |
|------|--------|
| `backend/app/routers/ops.py` | Reuse `main.response_orchestrator` singleton; typing on payloads |
| `backend/app/ops/service.py` | Clarify facade must not spawn a second engine for HTTP |
| `backend/app/main.py` | Drop unused `build_ops_health` import |
| `backend/app/core/config.py` | Comments: `api_key` / `metrics_enabled` reserved |
| `backend/app/routers/connectors.py` | Remove unused `request` param on `start_connector` |
| `backend/tests/test_ops.py` | Assert ops router shares main orchestrator |

### Frontend
| Path | Change |
|------|--------|
| `frontend/js/utils.js` | Shared `download()` helper |
| `frontend/js/app.js` | Use shared `esc`; remove local `escapeHtml`; escape org/site + timeline |
| `frontend/js/enterprise.js` | Shared `download`/`esc`; escape audit/history HTML |
| `frontend/js/enterprise8.js` | Shared `download`/`esc`; escape catalog/topology; export names `mercury-v16-*` |

### Documentation
| Path | Change |
|------|--------|
| `docs/SECURITY.md` | Align with reality (session RBAC; API key not enforced) |
| `IMPLEMENTATION_STATUS.md` | v16/V2.0 identity; remove false API-key claim |
| `docs/design/FINAL_CLEANUP_REPORT.md` | This report |

---

## What was intentionally not changed

Per “no new functionality” and audit P0 remediations deferred:

- Frontend `API_BASE` / WebSocket `:8000` hardcoding  
- CI workflow relocation to git root  
- Auth on open incident/ops GETs/POSTs  
- Docker `--workers 2` / shared session store  
- Wiring a new API-key dependency on routes  
- Alembic / durable approvals / decision Option B  
- Dual EventBus consolidation (larger refactor than cleanup)

---

## Duplicate / dead-code outcomes

| Audit item | Result |
|------------|--------|
| Dead `api_key.py` | Removed |
| Junk `tmp_*.txt` | Removed |
| Split ops orchestrator | Fixed — HTTP uses main singleton |
| Duplicate `download` | Consolidated in `utils.js` |
| Duplicate `escapeHtml` vs `esc` | Consolidated on `esc` |
| Unused imports/params | Cleaned in `main.py` / connectors |
| Empty `js/modules/` | Not present / nothing to delete |

---

## Test results

| Check | Result |
|-------|--------|
| `pytest -q backend/tests` | **70 passed** (+1 singleton regression) |
| `python -m compileall backend/app` | OK |
| `node --check` (utils, app, enterprise, enterprise8) | OK |

---

## Residual risk (unchanged by cleanup)

Critical/high items from `FINAL_RELEASE_AUDIT.md` that still require **hardening work** (not cleanup): CI path, compose URL mismatch, demo auto-login, unauthenticated reads, multi-worker sessions, full XSS surface beyond cleaned modules, tenant IDOR.

---

## Recommendation

Treat this cleanup as a **hygiene commit** before any P0 security/deploy fixes. Do not merge as “production ready” solely on this report.
