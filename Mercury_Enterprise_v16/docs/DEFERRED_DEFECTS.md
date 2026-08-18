# Deferred Defects

States: `open` · `deferred` · `transferred` · `completed` · `cancelled` · `closed`

Supports MEL/CDL linkage, dispatch category, repair interval, expiry, alert level (yellow/red).

`GET/POST /api/v1/planning/deferred-defects`  
`GET /api/v1/planning/deferred-defects/{id}` (`aircraft_id` filter on list)

Operator UI: Planning desk and aircraft Maintenance tab create defects; finding objects show MEL context. Tech-log create remains ACA release (no free-form logbook create API).
