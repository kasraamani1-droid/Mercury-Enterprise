# Inventory & Stock Ledger (Program B)

Stock truth is the immutable `logistics_stock_movements` ledger. Balances are derived and updated in the same transaction as each movement.

## Movement types

`receive`, `issue`, `transfer`, `adjust`, `return`, `scrap`, `repair`, `loan`, `exchange`, `reservation`, `release`

## Balances

`logistics_stock_balances` keyed by `(part_master_id, location_id, condition)` with `qty_on_hand` and `qty_reserved`.

Available = on_hand − reserved (oversell fails closed).

## Consumables

Part masters with `part_class=consumable` support min/max/reorder, shelf life, and `issue_policy` of `FIFO` or `FEFO` (lot/unit selection).

## API

- `GET /api/v1/logistics/stock/balances|units|movements`
- `POST /api/v1/logistics/stock/receive|issue|adjust|bulk-adjust|scrap`
- `GET/POST /api/v1/logistics/reservations`
- `GET /api/v1/logistics/dashboard`
- `GET /api/v1/logistics/shortages`

## Operator UI

Logistics Ops (`#logisticsWorkspace`) is the stores desk: live dashboard KPIs, location/condition filters, click-through part / material-request / PO / tool objects, waiting-parts job cards, and role-gated receive / issue / reserve / release / adjust / warehouse transfer.

Inventory is a **read-only** stock table that opens the same part objects. It does not duplicate mutations.

Available quantity is `qty_on_hand − qty_reserved` (also returned as `qty_available`). Oversell and insufficient reservation return HTTP 409; the UI shows the detail and does not retry.

Direct `POST /stock/issue` has no typed `work_order_id` / `job_card_id`. Job-card demand uses material requests (`job_card_id` + `work_order_id` on the header, then approve → reserve → issue).

Session roles (not aviation persona names): Viewer/Reviewer read; Operator/Administrator `logistics.stores`; Reviewer may use `logistics.tools`. Backend remains authoritative on 403.

See [MATERIAL_PLANNING.md](MATERIAL_PLANNING.md) · [BARCODE_RFID.md](BARCODE_RFID.md) · [JOB_CARDS.md](JOB_CARDS.md)
