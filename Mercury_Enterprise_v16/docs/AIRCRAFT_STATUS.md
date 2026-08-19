# Aircraft Status

Utilization counters (FH/FC/landings/engine/APU) live in `aircraft_utilization` (additive; does not alter fleet registry schema).

Traffic light: green · yellow · red  
Ops status: available · grounded · maintenance · ferry

`PUT /api/v1/planning/utilization`  
`GET /api/v1/planning/aircraft-status`

Omitted utilization counters (`flight_hours`, `flight_cycles`, landings, engine/APU hours) keep the stored values. Ops status and location are still replaced on each PUT.
