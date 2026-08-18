# EPIC-001 Platform Hardening — Engineering Notes

**Date:** 2026-08-14  
**Parent:** [MASTER_IMPLEMENTATION_BACKLOG.md](../implementation/MASTER_IMPLEMENTATION_BACKLOG.md)

## Delivered

| Task | Outcome |
|------|---------|
| Redis sessions + Compose | Delivered under EPIC-009; fail-closed startup when `REDIS_REQUIRED=true` |
| Event dual-write | `publish_sync` → `maybe_dual_write_to_fabric`; ownership matrix doc |
| Pagination | `PageParams`/`clamp_page`/`Query(le=500)` on fleet/org/personnel/publications/planning/approvals/incidents |
| Soft-delete policy | Documented selective policy (no mass column drop) |
| CI discoverability | `docs/engineering/CI.md` — workflows at parent git root |
| Health/ready Redis | `/ready` 503 + `/health` degraded when Redis required and unhealthy |
| Approvals package | Empty shell removed; **durable SQL `approval_requests`** (RC1 Blocker 03) with org/site list/approve/consume |
| File object store | `platform/file_storage.py` + `POST /api/v1/platform/files/upload` |

## Platform service checklist (RC)

| Concern | Status |
|---------|--------|
| Config validation | `Settings.validate_for_startup` (password, Secure cookies, Redis required) |
| Lifespan | Seed cascade + connectors start/stop in `main.py` |
| Health / ready / live / metrics | `core/health.py`, `/metrics` |
| Logging | `core/logging.py` request binding |
| DI | FastAPI `Depends(get_db)`, `require_session` |
| Exceptions | HTTPException domain pattern; middleware 429 |
| Audit | `record_audit` + platform `AuditEngine.require` |
| Events | Framework + Fabric dual-write for mapped types |
| Background | Connector heartbeat in lifespan |

## Deferred (under EPIC-001 only)

1. Live Redis CI job (Compose service in PR) — Medium  
2. Soft-delete write APIs for marketplace/network/plugins — Low (policy documents deferral)  
3. Cap remaining nested logistics/components catalog lists — Medium follow-up  
4. Extract approvals routes into a dedicated package — Low (optional cleanup; persistence done)
