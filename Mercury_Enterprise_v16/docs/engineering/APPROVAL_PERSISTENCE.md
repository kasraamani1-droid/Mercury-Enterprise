# Approval Persistence (RC1 Blocker 03)

**Status:** Implemented / verified 2026-08-17  
**Parent:** Mercury Platform RC1 Release Blocker Report (RB-03)

## Summary

Approval requests are stored in SQL table `approval_requests` (not an in-process dict). Rows survive process restart, logout/login, browser refresh (session cookie + GET), and a new database session (`pool_pre_ping` reconnects stale connections). List, approve, and consume are org/site scoped. Request / approve / consume write `audit_events` in the same transaction as the row change.

There is **no** reject API and **no** generic PATCH in this release. Status changes are approve (`pending` → `approved`) and consume (`consumed=true` on incident resolve/close). Optimistic locking is **not** implemented; write paths take `SELECT … FOR UPDATE` and return `409` on illegal transitions.

## API

| Method | Path | Permission | Behavior |
|--------|------|------------|----------|
| POST | `/api/v1/approvals` | `approval.request` | Persist pending approval stamped with session org/site |
| GET | `/api/v1/approvals` | `approval.review` | List current org/site (optional `status_filter`, capped pagination). Unfiltered list is the history. |
| POST | `/api/v1/approvals/{id}/approve` | `approval.review` | Approve if pending and in session tenant; else `404`/`409` |
| PATCH | `/api/v1/incidents/{id}/status` | `incident.update` | Non-admin resolve/close consumes a tenant-scoped approved row |

## Schema

Table `approval_requests`: `id`, `action`, `target_id`, `reason`, `status`, `requested_by`, `requested_role`, `organization_id`, `site_id`, `created_at`, `reviewed_by`, `reviewed_at`, `consumed`.

Alembic revision: `20260814_0022` (dev SQLite also creates via `ensure_schema()` / `Base.metadata.create_all`).

## Workflow

1. Operator `POST /approvals` → `pending` row + `approval.request` audit.
2. Reviewer `POST /approvals/{id}/approve` → `approved` + reviewer stamp + `approval.approve` audit.
3. Operator `PATCH /incidents/{id}/status` with `approval_id` → `consumed=true` + incident status + `approval.consume` audit (one commit).
4. Administrator may resolve/close without consuming an approval (existing RBAC).

Frontend Approvals Inbox (`frontend/js/ux2/workspaces.js`) loads `GET /approvals?status_filter=pending` with `credentials: include` and calls approve. It does not cache rows in `localStorage`; refresh re-fetches.

## Transactions and errors

| Case | Result |
|------|--------|
| Create / approve / consume | Mutate + audit then `db.commit()`; `get_db` closes/rolls back uncommitted work |
| Second approve | `409 Approval is not pending` |
| Consume while still pending | `409 Approval is not approved` |
| Second consume | `409 Approval already used` |
| Action or target mismatch | `409` |
| Missing `approval_id` on non-admin resolve | `400 Approval required` |
| Unknown or cross-tenant id | `404 Approval request not found` |
| Viewer | `403` on request/list/approve |
| Engine reconnect | SQLAlchemy `pool_pre_ping=True` |

## Audit trail

| Action | When |
|--------|------|
| `approval.request` | Create |
| `approval.approve` | Reviewer approve |
| `approval.consume` | Resolve/close with approval |

## Out of scope (not persistence defects)

- Reject / withdraw workflow
- Generic approval update PATCH
- Version-column optimistic locking
- Extracting routes from `main.py` into a package

## Regression tests

`backend/tests/test_approval_persistence.py` — SQL durability, restart simulation, logout/login, history list, audit trail, tenant isolation, RBAC, double approve/consume, consume error handling, cross-tenant consume denial. Companion: `test_audit.py`.
