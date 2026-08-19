# Workforce Planning

`workforce_plan_lines` assign technician / inspector / II / ACA / engineer / stores to work packages. Rows store planner-entered license / authorization / availability flags and workload hours. They are **not** a certification determination and do not compute MTBUR/MTBF.

## HTTP API

All routes require a session. Read: `planning.read` (Viewer / Reviewer / Operator / Administrator). Manage: `planning.manage` (Operator / Administrator). Tenant-scoped to the session organization.

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/api/v1/planning/workforce-plan-lines` | Optional `work_package_id`, `limit`, `offset` |
| `POST` | `/api/v1/planning/workforce-plan-lines` | Create. Employee and work package must belong to the same org |
| `GET` | `/api/v1/planning/workforce-plan-lines/{id}` | Workspace Engine inspect |
| `PATCH` | `/api/v1/planning/workforce-plan-lines/{id}` | Status, shift, hours, planner flags |

`role_code`: `technician` \| `inspector` \| `ii` \| `aca` \| `engineer` \| `stores`.

`status`: `planned` \| `assigned` \| `released` \| `complete` \| `cancelled`.

## Operator UI

Planning desk lists lines and (for Operator/Administrator) assigns a line to an existing work package and employee. Opening a row loads the Workspace Engine object. Work-order overview and aircraft Maintenance show package-linked lines.

## Seed / generation

Idempotent demo lines on `WP-DEMO-001` / `wp-demo-c-gmea` for E-1001 (technician), E-2001 (ACA), E-3001 (II). Generating a work package from a check creates the same default assignments when those employees exist.

Hangar bay assignment remains `GET/POST /api/v1/planning/hangar-plans`.
