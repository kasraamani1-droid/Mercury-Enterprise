# Maintenance Task Engine

Organization-scoped work orders integrated with the Technical Library, personnel certification, digital signatures, and the technical logbook.

## Task types

| Type | Code |
|------|------|
| Scheduled | `scheduled` |
| Unscheduled | `unscheduled` |
| Corrective | `corrective` |
| Preventive | `preventive` |
| Inspection | `inspection` |
| Functional check | `functional_check` |
| Operational check | `operational_check` |
| Troubleshooting | `troubleshooting` |
| Component replacement | `component_replacement` |
| Deferred defect | `deferred_defect` |
| MEL/CDL | `mel_cdl` |
| Service bulletin | `service_bulletin` |
| Engineering order | `engineering_order` |

## Lifecycle statuses

`open` → `assigned` → `started` (`in_progress` synonym) → `paused` → `completed` → certification gates (`awaiting_inspection` / `awaiting_aca`) → `released` → `closed`

Terminal without release: `rejected`, `cancelled`

Transitions: `POST /api/v1/maintenance/tasks/{id}/transition` (validated matrix + optional optimistic `expected_version`).

## Task fields

Task Number · ATA Chapter · Aircraft · Fleet · Organization · Priority · Status · Due Date · Estimated / Actual Hours · Publication Reference · Revision Used · Required Parts / Tools / Skills / Certification · Independent Inspection Required · ACA Required · Digital Signatures · Release Status · Version · Audit Trail

## Traceability chain

```
Aircraft → Component → Publication → Revision → Technician → Inspector → ACA
        → Technical Logbook (aircraft history) → Component History (on linked component)
        → Audit · Signature Chain
```

On `aircraft_released` Mercury writes:

1. Technical log entry (maintenance log / aircraft history)
2. Component history event `maintenance_release` when `component_id` is set
3. Audit events (`maintenance.certify`, `signature.create`, `logbook.entry.create`)
4. Signature chain via certification events

## Certification authority

Certify requires:

- Session user linked to the signing employee (Administrators may break-glass)
- Live password verification (`credential`) or PIN matched to active digital stamp
- Active qualification / authorization for the step (incl. expiry)
- Independent inspector ≠ performer and ≠ inspector
- ACA authorization for `aca_certified` and `aircraft_released`
- `certification.release` permission for aircraft release

## APIs

| Method | Path | Permission |
|--------|------|------------|
| GET | `/api/v1/maintenance/tasks` | `maintenance.read` (`limit`/`offset`, filters) |
| POST | `/api/v1/maintenance/tasks` | `maintenance.manage` |
| POST | `/api/v1/maintenance/tasks/{id}/transition` | `maintenance.manage` |
| GET | `/api/v1/maintenance/tasks/{id}/audit-trail` | `maintenance.read` |
| POST | `/api/v1/maintenance/tasks/{id}/certify` | `certification.sign` (+ release permission) |

## Related

[MAINTENANCE_CERTIFICATION.md](MAINTENANCE_CERTIFICATION.md) · [TECHNICAL_LIBRARY.md](TECHNICAL_LIBRARY.md) · [TECHNICAL_LOGBOOK.md](TECHNICAL_LOGBOOK.md) · [DIGITAL_SIGNATURES.md](DIGITAL_SIGNATURES.md) · [PERSONNEL.md](PERSONNEL.md) · [RBAC.md](RBAC.md)
