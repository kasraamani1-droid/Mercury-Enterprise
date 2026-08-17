# Digital Passport

Every Mercury object eventually receives a permanent **Digital Passport**.

## Passport kinds (examples)

| Kind | Typical entity types |
|------|----------------------|
| Aircraft | aircraft, fleet, configuration |
| Component | component, serialized_component, inventory_part |
| Engine / APU / Landing Gear | specialized component passports (same table, tags/kind) |
| Tool | tool, gse, calibration |
| Personnel | personnel, training, certificate, authorization |
| Organization | organization, facility, supplier, customer |
| Publication | publication, AD/SB/EO, academy_course |

## Recorded on every passport

- Ownership (`ownership_json`)
- History (`fabric_passport_history`)
- Events (`fabric_events`)
- Approvals / certificates (via events + attachment refs)
- Revisions (`version`)
- Relationships (`fabric_relationships`)
- Digital identity (`did:mercury:{org}:{type}:{id}`)
- Lifecycle (`draft|active|suspended|archived|retired`)
- AI metadata (`ai_metadata_json`)

## API

- `POST /api/v1/fabric/passports` — ensure (idempotent by org+type+id)
- `GET /api/v1/fabric/passports/{id}`
- `GET /api/v1/fabric/passports/{id}/history`
- `POST /api/v1/fabric/passports/{id}/lifecycle`

Legal hold blocks archive/retire until released.

## Digital Twin binding (Program 15)

Every Mercury Digital Twin links to a Fabric passport via `twin_objects.passport_id`.
See [DIGITAL_TWIN_ARCHITECTURE.md](DIGITAL_TWIN_ARCHITECTURE.md) and `GET /api/v1/twin/twins/{id}/passport`.
Passports never disappear when ownership or lifecycle state changes.
