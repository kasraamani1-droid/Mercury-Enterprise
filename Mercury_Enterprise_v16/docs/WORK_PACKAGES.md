# Work Packages

A **Work Package** is the planning container for one aircraft visit or check (A-check, layover, heavy visit).

## Hierarchy

```
Work Package → Work Orders → Job Cards → MaintenanceTask (certify / logbook)
```

## Fields

Package Number · Organization · Fleet · Aircraft · Registration · Description · Status · Priority · Scheduled Start/Finish · Actual Start/Finish · Planner · Supervisor · Hangar Bay · Shift · Estimated Hours · Actual Hours

## Statuses

`draft` → `planned` → `in_progress` → `completed` / `released` / `closed` / `cancelled`

Creating the first work order promotes `draft` → `planned`. Opening job cards promotes toward `in_progress`.

## APIs

| Method | Path | Permission |
|--------|------|------------|
| GET/POST | `/api/v1/work-orders/packages` | `work_order.read` / `work_order.manage` |
| GET | `/api/v1/work-orders/packages/{id}` | `work_order.read` |

## Related

[WORK_ORDERS.md](WORK_ORDERS.md) · [JOB_CARDS.md](JOB_CARDS.md) · [MAINTENANCE_EXECUTION.md](MAINTENANCE_EXECUTION.md) · [TECHNICIAN_WORKFLOW.md](TECHNICIAN_WORKFLOW.md)
