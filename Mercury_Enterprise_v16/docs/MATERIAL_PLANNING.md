# Material & Tool Planning Integration (Program B)

When Sprint 9 generates a work package from a check, Mercury:

1. Creates `parts_plan_lines` / `tool_plan_lines` from MPD requirements
2. Calls Program B `run_material_planning` / `run_tool_planning`
3. Reserves available stock or flags `shortage` / `purchase_required` (auto draft PR)
4. Reserves calibrated tools or flags `overdue_cal` / `unavailable`

## Direct APIs

- `POST /api/v1/logistics/material-planning/run`
- `POST /api/v1/logistics/tool-planning/run`
- `GET /api/v1/logistics/shortages`
- `GET/POST /api/v1/logistics/material-requests` (optional `work_order_id` / `job_card_id` filters)
- `POST /api/v1/logistics/material-requests/{id}/approve|reserve|issue|return|cancel`

## Operator bridge (Workspace Engine)

Job cards and work orders expose a **Materials** tab. Stores (Operator/Administrator) create a material request with `job_card_id` / `work_order_id`, then approve → reserve → issue. Returning unused qty requires `location_id` and per-line quantities.

`waiting_parts` on a job card is a maintenance status, not an automatic reservation. Logistics Ops lists those cards and opens `jobCard:{id}` with the materials tab.

There is no `aircraft_id` field on material requests. Aircraft context is preserved by opening the job card / work order object (which already carries `aircraft_id`).

Manual `POST /reservations` `source_type` is `manual|work_package|material_request|tool_plan` only — not `job_card`.
