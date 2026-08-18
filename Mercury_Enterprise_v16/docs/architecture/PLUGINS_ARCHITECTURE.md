# Mercury Plugin Platform — Architecture

**Program 16** · OEM and operational plugins for Mercury AEOS.

## Positioning

Eleven first-class plugins, each mapped to a Mercury Connect connector:

| Plugin | Connect connector | Notes |
|--------|-------------------|-------|
| Garmin | `oem.garmin` | Avionics / flight data — partial |
| Honeywell | `oem.honeywell` | Aerospace systems — partial |
| Drone Inspection | `inspection.drone` | UAS imagery — planned |
| NDT | `ndt.generic` | NDT evidence — partial |
| Flight Ops | `flight_ops.generic` | Schedule/status — planned |
| Accounting | `accounting.generic` | Finance bridge — ready |
| Custom Dashboards | `dashboard.custom` | Tenant widgets — ready |
| ERP | `erp.generic` | ERP bridge — ready |
| SMS | `safety.sms` | **Safety Management System** (not text SMS) — planned |
| Weather | `weather.generic` | METAR/TAF — partial |
| Fuel Planning | `fuel.planning` | Burn/uplift architecture — planned |

Live vendor SDKs are **future** Connect adapters. Secrets only via `vault://` config refs.

## Package

`backend/app/plugins/` → `/api/v1/plugins`  
Permissions: `plugins.read` / `plugins.manage`  
Alembic: `20260814_0019`

## Related

- Mercury Connect (`/api/v1/connect`)
- [PLUGINS_API.md](PLUGINS_API.md)
- [PLUGINS_PRODUCTION_READINESS.md](PLUGINS_PRODUCTION_READINESS.md)
- ADR-0016
