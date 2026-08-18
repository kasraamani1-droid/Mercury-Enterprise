# Planner Dashboard

`GET /api/v1/planning/dashboard`

KPIs: aircraft available/grounded · checks/AD/SB/EO due · deferred defects · waiting parts/engineering/inspection/ACA · traffic lights.

UI: **Planning** product tab (`frontend/js/planning.js`) plus aircraft **Maintenance** tab and Home due/forecast KPIs.

Due/forecast items link to aircraft objects and related work orders when a generated package or `linked_work_order_id` exists. Delayed work orders are listed from `GET /work-orders/orders` with status `delayed` (there is no separate planning delayed-items API). Generate WP uses `POST /planning/checks/generate-package` and can open the first returned work order. Returning to Planning keeps the area tab; object sessions stay in the Workspace Engine tab strip.

## Related

## Related

[FORECAST_ENGINE.md](FORECAST_ENGINE.md) · [HANGAR_PLANNING.md](HANGAR_PLANNING.md) · [WORKFORCE_PLANNING.md](WORKFORCE_PLANNING.md)
