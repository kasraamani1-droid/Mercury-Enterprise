# Digital Technical Logbook

On `aircraft_released`, the Maintenance Task Engine automatically creates an immutable technical log entry (aircraft maintenance history) containing:

Aircraft · Registration · Organization · ATA · Task number · Task · Publication · Revision · Revision number/date · Effective date · Required certification · Component · Serial · Mechanic · Inspector · Independent Inspector · ACA · Release signature · Signature chain · Summary

## APIs

| Method | Path | Permission |
|--------|------|------------|
| GET | `/api/v1/maintenance/logbook` | `logbook.read` |
| POST | `/api/v1/maintenance/logbook/{id}/amend` | `maintenance.manage` |

Entries are append-only; nothing is deleted or overwritten. Amendments create a **new** entry with `amendment_of=<original_id>` while the original remains unchanged. Per-task history also appears under `GET /api/v1/maintenance/tasks/{id}/audit-trail`.

There is **no** `POST /logbook` create route. Entries are written when certification reaches `aircraft_released` (job-card `/release` or task certify). List filters: `organization_id`, `aircraft_id` only — work-order linkage is shown in the UI by joining `task_id` to the job card's `maintenance_task_id`.

## Operator UI

Aircraft object → **Logbook** tab, or **Digital Logbook** area (`#logbookWorkspace`). Aircraft filter is sent as `aircraft_id`. Amend (Operator/Administrator) is append-only. Viewer can read; Reviewer can read but not amend.

## Related

## Related

[ACA_RELEASE.md](ACA_RELEASE.md) · [MAINTENANCE_TASKS.md](MAINTENANCE_TASKS.md) · [MAINTENANCE_CERTIFICATION.md](MAINTENANCE_CERTIFICATION.md) · [DIGITAL_SIGNATURES.md](DIGITAL_SIGNATURES.md)
