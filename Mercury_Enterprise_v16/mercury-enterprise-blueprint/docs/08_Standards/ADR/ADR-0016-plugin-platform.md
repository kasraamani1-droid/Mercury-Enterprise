# ADR-0016 — Mercury Plugin Platform

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-08-14 |
| Related | ADR-0009, ADR-0012, ADR-0013 |

## Context

Mercury needs first-class surfaces for Garmin, Honeywell, drone inspection, NDT, flight ops, accounting, dashboards, ERP, safety SMS, weather, and fuel planning — without embedding live vendor SDKs in the core monolith prematurely.

## Decision

1. Introduce `backend/app/plugins/` as the Plugin Platform product catalog.
2. Map every plugin to a Mercury Connect connector code.
3. Org enablement via installations with vault-only secret refs.
4. Custom Dashboards as a plugin with tenant layout JSON.
5. Interpret **SMS** as Safety Management System; keep cellular SMS as `connect` `sms.generic`.
6. Mark OEM/drone/safety/fuel adapters as readiness (partial/planned) until live adapters ship.

## Consequences

- Clear plugin marketplace path later
- Connect remains the integration facade
- Product copy must distinguish Safety SMS vs text SMS
