# Marketplace — Entity Relationship

```
Organization
    │
    ├── MarketplaceSeller (1..n profiles / seller types)
    │       └── MarketplaceProduct (catalog offers)
    │               ├── MarketplaceCartItem (per user)
    │               ├── MarketplaceFavorite
    │               ├── MarketplaceQuote ──► MarketplaceOrder
    │               │                              └── MarketplaceOrderLine
    │               └── MarketplaceReview
    │
    ├── MarketplaceListing (legacy readiness rows; optional product.listing_id)
    └── MarketplaceSavedSearch (per user query JSON)
```

## Core tables (Program 13)

| Table | Purpose |
|-------|---------|
| `marketplace_sellers` | Seller digital profiles + badge JSON |
| `marketplace_products` | Catalog SKUs / services / jobs / training |
| `marketplace_cart_items` | Buyer cart |
| `marketplace_quotes` | Digital RFQ / quotes |
| `marketplace_orders` | Orders (payment_status architecture) |
| `marketplace_order_lines` | Line items |
| `marketplace_reviews` | Ratings / reviews |
| `marketplace_favorites` | Saved products |
| `marketplace_saved_searches` | Saved filter queries |
| `marketplace_listings` | Legacy AEOS listings (retained) |

## Key fields

- Products: `offer_mode` (sale|rental|service|training|job), serial/batch flags, certificates/warranty/compatibility/supersessions/alternates/publications JSON, `ai_metadata_json`.
- Sellers: `verification_badges_json` + fixed `verification_disclaimer`.
- Orders: `payment_status=not_configured` until PSP integration.

Alembic: `20260814_0016`.
