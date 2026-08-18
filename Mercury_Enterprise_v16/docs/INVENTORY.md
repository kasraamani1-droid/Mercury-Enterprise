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
