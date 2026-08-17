# Purchasing (Program B)

End-to-end procurement workflow:

Purchase Request → Approval → RFQ → Vendor Selection → Purchase Order → Receiving → Inspection → Putaway → Invoice → Closed

## Purchase orders

Multi-vendor RFQ quotes, currency, tax, shipping, expected delivery, partial deliveries / back orders, returns & warranty terms.

## API

- `GET/POST /api/v1/logistics/purchase-requests` (+ approve, rfq)
- `GET /api/v1/logistics/rfqs` (+ quotes, select, purchase-order)
- `GET /api/v1/logistics/purchase-orders` (+ receive, invoices, close)
- `POST /api/v1/logistics/receipts/{id}/inspect|putaway`
