# Work Packages & Work Orders

Sprint 8 adds organization-scoped **Work Packages** and **Work Orders** for airline/MRO maintenance planning and execution. Job cards (executable tasks) live under work orders — see [JOB_CARDS.md](JOB_CARDS.md) and [MAINTENANCE_EXECUTION.md](MAINTENANCE_EXECUTION.md).

## Hierarchy

```
Work Package (aircraft visit / check)
  └── Work Order (ATA / scope group)
        └── Job Card (single task) → MaintenanceTask (certify / logbook)
```

## Work Package fields

Package Number · Organization · Fleet · Aircraft · Registration · Description · Status · Priority · Scheduled Start/Finish · Actual Start/Finish · Planner · Supervisor · Hangar Bay · Shift · Estimated Hours · Actual Hours

Statuses: `draft` → `planned` → `in_progress` → `completed` / `released` / `closed` / `cancelled`

## Work Order fields

WO Number · Organization · Aircraft · ATA · Status · Priority · Planner · Supervisor · Work Package · Due Date · Estimated/Actual Hours · Related Publication + Revision

Statuses: `draft` | `open` | `in_progress` | `delayed` | `completed` | `released` | `closed` | `cancelled`

Creating the first work order promotes a package from `draft` → `planned`. Creating job cards promotes orders/packages toward `in_progress`.

## APIs

| Method | Path | Permission |
|--------|------|------------|
| GET | `/api/v1/work-orders/packages` | `work_order.read` |
| POST | `/api/v1/work-orders/packages` | `work_order.manage` |
| GET | `/api/v1/work-orders/packages/{id}` | `work_order.read` |
| GET | `/api/v1/work-orders/orders` | `work_order.read` |
| POST | `/api/v1/work-orders/orders` | `work_order.manage` |
| GET | `/api/v1/work-orders/orders/{id}` | `work_order.read` |
| GET | `/api/v1/work-orders/dashboard` | `work_order.read` |
| GET | `/api/v1/work-orders/reports/{report}` | `work_order.read` |

Reports: `open_work_orders`, `delayed_work_orders`, `labor_hours`, `aircraft_status`, `technician_productivity`, `inspection_status`, `release_status`.

## Isolation & audit

Every package/order is org-scoped. Cross-org access returns 403. Create/assign/transition/inspect/release actions emit audit events (`work_package.create`, `work_order.create`, `job_card.*`).

## Related

[JOB_CARDS.md](JOB_CARDS.md) · [MAINTENANCE_EXECUTION.md](MAINTENANCE_EXECUTION.md) · [MAINTENANCE_TASKS.md](MAINTENANCE_TASKS.md) · [RBAC.md](RBAC.md)
