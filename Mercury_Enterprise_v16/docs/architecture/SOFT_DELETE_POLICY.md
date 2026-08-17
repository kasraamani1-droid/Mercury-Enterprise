# Soft-Delete Policy (EPIC-001)

**Status:** Active for Platform 1.0 RC

## Decision

Mercury uses **selective soft-delete**, not a universal `deleted_at` pattern.

| Class | Behavior |
|-------|----------|
| **Active soft-delete** | Platform files (`DELETE /api/v1/platform/files/{id}`), Fabric relationships (unlink) — set `deleted_at` + filter out of lists |
| **Filter-ready columns** | Marketplace, Network, Plugins, Connect, Ecosystem, Planning, Logistics, Platform org entities — columns exist and lists filter `deleted_at IS NULL`, but **RC does not expose delete APIs** that set the column |
| **Hard / status lifecycle** | Fleet aircraft, work orders, org memberships — use status fields (`active`/`archived`) rather than `deleted_at` |
| **Immutable** | Enterprise event store — never soft-deleted |

## RC rules

1. Do **not** drop unused `deleted_at` columns in RC (migration risk); document and keep filters.
2. New delete endpoints must soft-delete when the model already has `deleted_at`.
3. Tenant isolation still applies to soft-deleted rows (no cross-org recovery leaks).
4. Post-RC: either wire product/seller/plugin uninstall soft-deletes **or** remove unused columns in a dedicated migration epic.

## Rationale

Additive RC hardening prefers documenting intent over mass schema churn that would block Platform 1.0.
