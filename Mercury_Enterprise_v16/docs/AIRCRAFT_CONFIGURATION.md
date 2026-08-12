# Aircraft Components & Configuration Management

Sprint 7 adds ATA-linked component catalog, serialized component tracking, installation history, and aircraft configuration views on top of the Aircraft Registry.

## Domain

```
AtaChapter (shared)
ComponentCatalogItem (shared part numbers)
  └── SerializedComponent (organization-scoped)
        └── ComponentInstallationHistory (immutable)

Aircraft configuration = currently installed SerializedComponents for an aircraft
```

Major assemblies are modeled via `component_type` (`engine`, `apu`, `landing_gear`, …) and free-form `installation_position` (e.g. `ENG1`, `NLG`) — not hardcoded to a single aircraft type.

## Time / cycles / life limits

| Field | Meaning |
|-------|---------|
| TSN / CSN | Time / cycles since new |
| TSO / CSO | Time / cycles since overhaul |
| aircraft_*_at_install | Snapshot at install |
| remaining_* | Derived from limits − TSN/CSN |

Hours use `Numeric(12,2)` decimal storage. Removal advances TSN/CSN/TSO/CSO by the delta between removal and install aircraft values.

## Isolation & concurrency

- Operational rows carry `organization_id` and membership checks.
- Serial unique per organization.
- A component cannot be removed unless it is currently `installed`.
- A component cannot be `installed` twice; position occupancy is unique per aircraft (`uq_aircraft_position_occupant`).
- Install, remove, and transfer each run in a **single DB transaction** (row lock via `FOR UPDATE` where supported; transfer remove+reinstall shares one commit).
- History rows are append-only.

## Permissions

| Permission | Roles |
|------------|-------|
| `component.read` / `configuration.read` | Viewer+ |
| `component.manage` / `configuration.manage` | Operator+ |
| ATA / catalog writes | Platform Administrator |

## REST (`/api/v1/components`)

| Method | Path |
|--------|------|
| GET/POST | `/ata-chapters` |
| GET/POST | `/catalog` |
| GET/POST | `/serialized` |
| GET | `/serialized/{id}` |
| POST | `/serialized/{id}/install` |
| POST | `/serialized/{id}/remove` |
| POST | `/serialized/{id}/transfer` |
| PATCH | `/serialized/{id}/life-limits` |
| PATCH | `/serialized/{id}/time-cycles` |
| GET | `/serialized/{id}/history` |
| GET | `/history` |
| GET | `/aircraft/{aircraft_id}/configuration` |

## Database

- Models: `backend/app/components/models.py`
- Alembic: `20260812_0004_aircraft_components`

## Out of scope

Work orders, MPD, AD/SB compliance, predictive maintenance, and AI forecasting.
