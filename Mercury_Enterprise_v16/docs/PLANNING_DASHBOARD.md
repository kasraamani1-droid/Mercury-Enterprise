# Planner Dashboard

`GET /api/v1/planning/dashboard`

KPIs: aircraft available/grounded · checks/AD/SB/EO due · deferred defects · waiting parts/engineering/inspection/ACA · traffic lights.

UI: **Planning** product tab (`frontend/js/planning.js`) is the planner desk: live KPIs, filters, role-gated mutations, and click-through Workspace Engine objects (check, AD, SB, EO, finding, MEL). Aircraft **Maintenance** can log deferred defects. Engineering lists the same AD/SB/EO objects.

Due/forecast items open the matching object (check / AD / SB / EO / finding) plus aircraft and related work orders when a generated package or `linked_work_order_id` exists. Delayed work orders are listed from `GET /work-orders/orders` with status `delayed`. Generate WP uses `POST /planning/checks/generate-package` with an **operator-selected** check (duplicate generate returns HTTP 409).

GET-by-id (read): `/checks/{id}`, `/ads/{id}`, `/service-bulletins/{id}`, `/engineering-orders/{id}`, `/deferred-defects/{id}`, `/mel-items/{id}`.

Session roles: Viewer/Reviewer read; Operator/Administrator `planning.manage`. Aviation Planner names remain documentation-only.

## Related

[FORECAST_ENGINE.md](FORECAST_ENGINE.md) · [HANGAR_PLANNING.md](HANGAR_PLANNING.md) · [WORKFORCE_PLANNING.md](WORKFORCE_PLANNING.md)
