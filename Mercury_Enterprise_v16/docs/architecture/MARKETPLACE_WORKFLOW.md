# Marketplace — Workflows

## Seller onboarding

1. Org enrolls in marketplace ecosystem (Program 12).
2. Create `MarketplaceSeller` profile (type, capabilities, locations, badge markers).
3. Publish `MarketplaceProduct` rows (category, pricing, availability, docs/certs refs).
4. Optional: link Fabric passport / legacy listing.

## Buyer discovery → purchase

```
Search / category browse
        │
        ▼
Product detail (pricing + inventory APIs)
        │
   ┌────┴────┐
   ▼         ▼
Favorite   Cart
   │         │
   └────┬────┘
        ▼
   Create Quote
        ▼
   Create Order (from quote or direct product)
        ▼
   Shipping / invoice refs (structured)
        ▼
   Review / rating (updates seller aggregates)
```

## Repair / calibration / training / jobs

Same product model with `offer_mode` and category:

- **service** + repair/cal categories → turnaround_days, quote_required availability
- **training** → scheduled seats as qty
- **job** → careers listing as catalog offer (AI matching metadata only)
- **rental** → special tools share/rent path

## Status machines (initial)

- Quote: draft → sent → accepted | rejected | expired
- Order: draft → submitted → quoted → accepted → fulfilled → shipped → completed | cancelled

Payment remains `not_configured` until Connect payment adapter binds.
