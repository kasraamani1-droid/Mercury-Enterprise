# Job Cards

A **Job Card** is one executable maintenance task inside a Work Order. Each card links to a **MaintenanceTask** so certification, digital signatures, technical logbook, and aircraft/component history reuse the Sprint 7 engine (no duplicate certify path).

## Fields

Description · ATA · Publication · Revision · Required Parts · Required Tools · Required Certification · Required Skill · Estimated/Actual Hours · Technician · Inspector · Independent Inspector · ACA · Hangar Bay · Attachments · Photos · Notes · Independent Inspection Required · ACA Required

## Status lifecycle

```
Draft → Assigned → Accepted → In Progress ⇄ Paused
                              ↘ Waiting Parts / Waiting Engineering
                              → Waiting Inspection → Completed → Released → Closed
                                                   ↘ Rejected → In Progress / Assigned
```

Validated transitions are enforced in `WorkOrderService.JC_TRANSITIONS`. Invalid transitions return HTTP 409.

**Certification gates are not reachable via `/transition`:** `waiting_inspection`, `completed`, and `released` may only be entered through `complete-work`, `inspect`, and `release` respectively.

| Status | Meaning |
|--------|---------|
| `draft` | Created, unassigned |
| `assigned` | Technician assigned |
| `accepted` | Technician accepted the card |
| `in_progress` | Work started |
| `paused` | Temporarily stopped |
| `waiting_parts` | Blocked on stores |
| `waiting_engineering` | Blocked on engineering |
| `waiting_inspection` | Work performed; awaiting QA |
| `completed` | Inspection approved (may still need II / ACA) |
| `rejected` | Inspection rejected |
| `released` | ACA release complete (logbook written) |
| `closed` | Terminal administrative close |

## APIs

| Method | Path | Permission |
|--------|------|------------|
| GET/POST | `/api/v1/work-orders/job-cards` | read / manage |
| POST | `/api/v1/work-orders/job-cards/{id}/assign` | manage |
| POST | `/api/v1/work-orders/job-cards/{id}/transition` | execute |
| POST | `/api/v1/work-orders/job-cards/{id}/complete-work` | execute |
| POST | `/api/v1/work-orders/job-cards/{id}/inspect` | execute |
| POST | `/api/v1/work-orders/job-cards/{id}/release` | `certification.release` |
| GET/POST | `/api/v1/work-orders/job-cards/{id}/attachments` | read / execute |

## Certify bridge

- Create job card → creates linked `MaintenanceTask` with same publication revision binding  
- Complete work → signs `performed` → status `waiting_inspection`  
- Inspect approve → signs `inspected` (or `independent_inspection`) → `completed`  
- ACA release → signs `aca_certified` (if required) + `aircraft_released` → technical logbook + history  

Segregation of duties: independent inspector ≠ performer and ≠ inspector (see personnel seed E-1001 / E-2001 / E-3001).

## Related

[WORK_ORDERS.md](WORK_ORDERS.md) · [MAINTENANCE_EXECUTION.md](MAINTENANCE_EXECUTION.md) · [MAINTENANCE_CERTIFICATION.md](MAINTENANCE_CERTIFICATION.md) · [DIGITAL_SIGNATURES.md](DIGITAL_SIGNATURES.md)
