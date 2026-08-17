# EPIC-003 Backend Completion — Engineering Notes

**Date:** 2026-08-14  
**Parent:** [MASTER_IMPLEMENTATION_BACKLOG.md](../implementation/MASTER_IMPLEMENTATION_BACKLOG.md)

## Delivered

| Task | Outcome |
|------|---------|
| Pilot CRUD | Registration GET/PATCH; aircraft create + registration create already present |
| Marketplace org scope | Cart/quotes/orders assert org access; regression tests added |
| Temp access / custom roles | `security/runtime_authz.py` + all domain `require_*` use `PermissionService` |
| Logistics PO workflow | `PO_WORKFLOW_CODE` on WorkflowBridge; create/receive/close sync |
| Publications local FS | `local_filesystem` storage kind under `MERCURY_PUBLICATIONS_STORAGE_ROOT` |
| Approvals package | Already removed (EPIC-001); APIs remain in `main.py` |
| OpenAPI tags | Descriptions for Programs 13–17 (+ fleet/platform/logistics/work-orders/org) |

## Runtime authz

Routers call `require_allowed(db, session, perms, any_of=...)` which unions:

1. Session role matrix (`has_permissions`)
2. Active `PlatformTemporaryAccess` grants for the session org
3. Custom roles referenced as `role:<code>` in temp grants

Tests revoke active temp grants after each case (`conftest` autouse) to prevent leakage on the shared SQLite DB.

## Remaining under EPIC-003 only

1. Optional: PATCH registration `make_current` UI binding (API ready) — Low  
2. Optional: revoke temporary-access HTTP endpoint (tests revoke via DB) — Low  
3. Nested catalog list caps already tracked under EPIC-001 — not duplicated here  
