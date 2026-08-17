# Warehouse Management (Program B)

Enterprise warehouse hierarchy for Mercury logistics.

## Hierarchy

`Warehouse → Building → Store → Room → Zone → Aisle → Shelf → Bin → Location`

Locations are the pickable leaf (or area) used by stock balances and movements.

## Location / zone types

- `general`, `receiving`, `shipping`, `quarantine`, `hazmat`, `bonded`, `virtual`

Warehouses may be `physical`, `virtual`, or `bonded`.

## Transfers

`POST /api/v1/logistics/transfers` creates a transfer; `.../complete` moves qty between locations and writes immutable stock movements.

## API

- `GET/POST /api/v1/logistics/warehouses`
- `POST /api/v1/logistics/warehouses/tree` — create full demo-ready tree
- `GET/POST /api/v1/logistics/locations`
- `GET/POST /api/v1/logistics/transfers`
