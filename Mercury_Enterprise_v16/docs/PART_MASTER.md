# Part Master (Program B)

Logistics-owned catalog for stores and purchasing. Optionally links to Sprint 7 `component_catalog` via `catalog_item_id` (configuration remains authoritative for aircraft install).

## Attributes

OEM / customer part number, manufacturer, ATA, NSN, class (consumable/rotable), weight/dimensions, shelf life, hazmat / DG / RoHS, certificates & attachments (URI metadata), barcodes / QR / RFID identifiers, families, supersessions / alternates / interchangeable relations.

## API

- `GET/POST /api/v1/logistics/parts`
- `POST /api/v1/logistics/identifiers`
- `POST /api/v1/logistics/parts/{id}/attachments`
- `GET/POST /api/v1/logistics/families`
- `GET/POST /api/v1/logistics/supersessions`
