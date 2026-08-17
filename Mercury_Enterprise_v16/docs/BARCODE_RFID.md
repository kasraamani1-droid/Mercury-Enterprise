# Barcode / QR / RFID (Program B)

Identifiers attach to part masters, stock units, or tools (`barcode|qr|rfid`).

## Scan API (mobile-ready)

`POST /api/v1/logistics/scan` with `{ "value": "..." }` resolves the identifier and returns part/unit/tool context plus balances when applicable.

No native mobile client ships in this release; hangar/mobile apps consume the same REST contract.
