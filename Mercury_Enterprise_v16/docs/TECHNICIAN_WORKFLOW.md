# Technician Workflow

## Board actions

My Assigned Work · Accept · Start · Pause · Resume · Request Parts · Request Engineering · Complete · Notes / Photos · Library shortcuts (AMM/IPC/WDM/FIM)

## Valid path

```
Assigned → Accepted → In Progress ⇄ Paused / Waiting Parts / Waiting Engineering
                   → Complete Work (signs performed) → Waiting Inspection
```

Technicians **cannot**:

- Transition into `waiting_inspection`, `completed`, or `released` via `/transition`
- Inspect or ACA-release work
- Mutate attachments/notes on `released` / `closed` cards
- Sign inspection for work they performed (segregation of duties)

## Complete work

`POST /api/v1/work-orders/job-cards/{id}/complete-work` requires live credential, linked employee binding, and writes the `performed` certification event on the linked MaintenanceTask.

## Offline

Transitions and complete-work payloads may queue in `localStorage` and flush when online. Offline complete always syncs through `complete-work` (never a bare status transition).

## Related

[JOB_CARDS.md](JOB_CARDS.md) · [ACA_RELEASE.md](ACA_RELEASE.md) · [TECHNICAL_LIBRARY.md](TECHNICAL_LIBRARY.md)
