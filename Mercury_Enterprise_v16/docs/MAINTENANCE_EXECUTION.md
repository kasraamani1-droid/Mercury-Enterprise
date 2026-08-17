# Maintenance Execution (Sprint 8)

End-to-end MRO workflow delivered by the Work Orders module and Maintenance workspace UI.

## Business flow

```
Planning → Work Package → Work Order → Job Cards
  → Technician Assignment → Maintenance Execution
  → Inspection → Independent Inspection (if required)
  → ACA Release → Technical Logbook → Aircraft History → Audit
```

## Role boards (UI)

| Board | Actions |
|-------|---------|
| Planner | Planning board, packages/orders, hangar bay & shift, library shortcuts |
| Supervisor | Assign / reassign, monitor progress, bay assignment |
| Technician | My work, start/pause/resume/complete, notes/photos, offline queue |
| QA / Inspector | Approve, reject, require rework, independent inspection |
| ACA | Final release with electronic signature → logbook |
| Manager | Cross-role dashboards + open WO report |

Offline-ready: technician transitions and notes can queue in `localStorage` and flush when online.

## Dashboards

`GET /api/v1/work-orders/dashboard?role=` manager | planner | supervisor | technician | qa | aca

KPIs: open WOs, delayed WOs, job cards by status, awaiting inspection, awaiting release.

## Reports

`GET /api/v1/work-orders/reports/{name}` — open/delayed work orders, labor hours, aircraft status, technician productivity, inspection status, release status.

## Personas & RBAC

Session roles map to permissions `work_order.read|manage|execute` plus certification/release. Aviation personas (Technician, Inspector, ACA, Planner, Supervisor, Stores, Engineering, QA, Manager, Administrator) are documented in [RBAC.md](RBAC.md). Organization isolation applies on every list/get/mutate path.

## Architecture notes

- Package: `backend/app/work_orders/` — models, repository, service, thin router  
- Reuses `MaintenanceService.sign_action` for certify/logbook (no duplicated engine)  
- Alembic: `20260813_0009_work_orders_job_cards`  
- Frontend: `frontend/js/maintenance.js` + Maintenance product tab  

## Related

[WORK_ORDERS.md](WORK_ORDERS.md) · [JOB_CARDS.md](JOB_CARDS.md) · [TECHNICAL_LOGBOOK.md](TECHNICAL_LOGBOOK.md) · [TECHNICAL_LIBRARY.md](TECHNICAL_LIBRARY.md) · [AUDIT_LOGGING.md](AUDIT_LOGGING.md)
