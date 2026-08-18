# Tool Control (Program B)

Enterprise tool crib: tools, calibration, kits, shadow boards, issue/return, reservations, lost tool reports, append-only tool history.

## Calibration

Tools with `calibration_required` cannot be planned/issued when overdue. Calibration certificates stored as number + URI metadata.

## API

- `GET/POST /api/v1/logistics/tools`
- `POST /api/v1/logistics/tools/{id}/calibrate|reserve|issue|return|lost`
- `GET /api/v1/logistics/tools/{id}/history|calibrations`
- `GET /api/v1/logistics/lost-tool-reports`
- `POST /api/v1/logistics/tool-planning/run`

Open a tool from Logistics Ops to issue, return, or calibrate. Reviewer has `logistics.tools`; Viewer does not mutate.
