# Maintenance Certification

Certification chain for maintenance tasks (see [MAINTENANCE_TASKS.md](MAINTENANCE_TASKS.md) for the full task engine):

```
Performed By → Inspector → Independent Inspection (if required) → ACA Certification → Aircraft Release
```

## Critical task policies

Configurable per organization/domain (engine, flight controls, landing gear, fuel, structural, propulsion, general). At task create, policy flags are copied onto the task (`requires_inspector`, `independent_inspection_required`, `aca_required`). Certify uses those task flags only.

## Roles involved

Mechanic / Licensed AME · Inspector · Independent Inspector · ACA · Chief Engineer / QA (via permissions)

## APIs

`POST /api/v1/maintenance/tasks/{id}/certify` with step + signature method (+ optional `actual_hours`).

Release step requires `certification.release` (Reviewer+) or Administrator and sets `release_status=released`, then auto-creates a technical log entry.

## Related

[MAINTENANCE_TASKS.md](MAINTENANCE_TASKS.md) · [DIGITAL_SIGNATURES.md](DIGITAL_SIGNATURES.md) · [TECHNICAL_LOGBOOK.md](TECHNICAL_LOGBOOK.md) · [PERSONNEL.md](PERSONNEL.md)
