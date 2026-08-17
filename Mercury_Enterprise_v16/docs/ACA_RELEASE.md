# ACA Release

Final release to service for a Job Card / linked MaintenanceTask.

## Preconditions (all required)

1. Job card status = `completed` (inspection approved; independent inspection signed when required)
2. Certification events present: `performed`, `inspected` (+ `independent_inspection` if required)
3. Immutable publication revision bound on the job card (`publication_id` + `publication_revision_id`)
4. ATA chapter present
5. Session permission `certification.release`
6. Signer has active ACA authorization and live credential

## Release effects

1. Signs `aca_certified` when `aca_required`
2. Signs `aircraft_released` (duplicate release blocked)
3. Creates immutable technical logbook entry with publication, revision, revision number/date, ATA, certificate requirements, signature chain
4. Updates aircraft / component history when applicable
5. Sets job card status `released` and rolls package/order status
6. Fail-closed audit event `job_card.release`

## Forbidden bypasses

- `/transition` to `released` → HTTP 409
- Release before inspection → HTTP 409
- Double release → HTTP 409
- Release without publication revision → HTTP 409

## Logbook amendments

Original entries are never updated. Corrections use append-only  
`POST /api/v1/maintenance/logbook/{entry_id}/amend`.

## Related

[JOB_CARDS.md](JOB_CARDS.md) · [TECHNICAL_LOGBOOK.md](TECHNICAL_LOGBOOK.md) · [MAINTENANCE_CERTIFICATION.md](MAINTENANCE_CERTIFICATION.md) · [DIGITAL_SIGNATURES.md](DIGITAL_SIGNATURES.md)
