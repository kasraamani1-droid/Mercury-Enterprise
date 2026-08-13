# Digital Technical Logbook

On `aircraft_released`, the Maintenance Task Engine automatically creates an immutable technical log entry (aircraft maintenance history) containing:

Aircraft · Registration · Organization · ATA · Task number · Task · Publication · Revision · Component · Serial · Mechanic · Inspector · ACA · Release signature · Summary

## APIs

`GET /api/v1/maintenance/logbook` (`logbook.read`)

Entries are append-only; nothing is deleted. Per-task history also appears under `GET /api/v1/maintenance/tasks/{id}/audit-trail`.

## Related

[MAINTENANCE_TASKS.md](MAINTENANCE_TASKS.md) · [MAINTENANCE_CERTIFICATION.md](MAINTENANCE_CERTIFICATION.md) · [DIGITAL_SIGNATURES.md](DIGITAL_SIGNATURES.md)
