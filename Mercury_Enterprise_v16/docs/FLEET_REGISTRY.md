# Aircraft Registry & Fleet Management

Sprint 6 adds a production-oriented aviation registry on top of Mercury’s organization tenancy.

## Domain model

```
Manufacturer (shared catalog)
  └── AircraftModel (shared catalog)
AircraftStatus (shared lookup)

Organization (tenant)
  ├── FleetOperator   (aviation AOC / airline operator)
  ├── Fleet
  ├── Aircraft        → model, fleet?, operator?, status_code
  └── Registration    → aircraft, globally unique registration_mark
```

`FleetOperator` is deliberately named to avoid collision with Mercury’s RBAC **Operator** role.

## Isolation

| Resource | Scope |
|----------|--------|
| Manufacturers, models, statuses | Shared catalog |
| Fleet operators, fleets, aircraft, registrations | `organization_id` + membership checks |

Cross-org reads/writes return **403** / **404** using the same membership rules as Sprint 5.

## Permissions

| Permission | Roles | Use |
|------------|-------|-----|
| `fleet.read` | Viewer+ | List/read catalog and org fleet data |
| `fleet.manage` | Operator, Administrator | Create aircraft/fleets/operators/registrations; status updates |
| Catalog writes | Platform Administrator (`admin.system`) | Manufacturers / models |

## REST API (`/api/v1/fleet`)

| Method | Path |
|--------|------|
| GET/POST | `/manufacturers` |
| GET/POST | `/models` |
| GET | `/statuses` |
| GET/POST | `/operators` |
| GET/POST | `/fleets` |
| GET/POST | `/aircraft` |
| GET | `/aircraft/{id}` |
| PATCH | `/aircraft/{id}/status` |
| GET/POST | `/registrations` |

Mutations emit audit actions (`fleet.aircraft.create`, `fleet.registration.create`, …).

## Seed data

- Statuses: `active`, `maintenance`, `grounded`, `reserved`, `retired`
- Manufacturers: Airbus, Boeing (+ A320 / B738 models)
- East org demo: Mercury East Airlines, East Narrowbody fleet, `C-GMEA` / `C-GMEB`

## Database

- Models: `backend/app/fleet/models.py`
- Alembic: `20260812_0003_aircraft_registry` (after `20260812_0002`)
- SQLite/dev: `ensure_schema()` imports fleet models into `create_all`

## Dashboard

`GET /api/v1/dashboard/summary` → `fleet_health.aircraft_online` counts org aircraft with an operational status.
