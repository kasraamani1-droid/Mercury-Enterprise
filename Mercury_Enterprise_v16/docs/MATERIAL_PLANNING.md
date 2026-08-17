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
