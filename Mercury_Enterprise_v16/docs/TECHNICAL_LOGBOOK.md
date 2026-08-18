# Digital Technical Logbook

On `aircraft_released`, the Maintenance Task Engine automatically creates an immutable technical log entry (aircraft maintenance history) containing:

Aircraft · Registration · Organization · ATA · Task number · Task · Publication · Revision · Revision number/date · Effective date · Required certification · Component · Serial · Mechanic · Inspector · Independent Inspector · ACA · Release signature · Signature chain · Summary

## APIs

| Method | Path | Permission |
|--------|------|------------|
| GET | `/api/v1/maintenance/logbook` | `logbook.read` |
| POST | `/api/v1/maintenance/logbook/{id}/amend` | `maintenance.manage` |

Entries are append-only; nothing is deleted or overwritten. Amendments create a **new** entry with `amendment_of=<original_id>` while the original remains unchanged. Per-task history also appears under `GET /api/v1/maintenance/tasks/{id}/audit-trail`.

## Related

[ACA_RELEASE.md](ACA_RELEASE.md) · [MAINTENANCE_TASKS.md](MAINTENANCE_TASKS.md) · [MAINTENANCE_CERTIFICATION.md](MAINTENANCE_CERTIFICATION.md) · [DIGITAL_SIGNATURES.md](DIGITAL_SIGNATURES.md)
