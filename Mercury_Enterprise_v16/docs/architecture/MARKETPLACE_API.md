# Marketplace API

Base: `/api/v1/marketplace`  
Permissions: `marketplace.read` | `marketplace.manage` (also platform/org read for list/overview).

## Surfaces

| Area | Methods | Paths |
|------|---------|-------|
| Overview | GET | `/overview` |
| Catalog | GET | `/categories` |
| Listings (legacy) | GET, POST | `/listings` |
| Supplier | GET, POST, GET | `/sellers`, `/sellers/{id}` |
| Catalog products | GET, POST, GET | `/products`, `/products/{id}` |
| Pricing | GET | `/products/{id}/pricing` |
| Inventory | GET | `/products/{id}/inventory` |
| Search | GET | `/search?q=&category=` |
| Cart | GET, POST | `/cart` |
| Quotes | GET, POST | `/quotes` |
| Orders | GET, POST, GET | `/orders`, `/orders/{id}` |
| Reviews | GET, POST | `/reviews` |
| Favorites | GET, POST | `/favorites` |
| Saved searches | GET, POST | `/saved-searches` |

## Notes

- All mutating routes require `marketplace.manage`.
- Tenant isolation enforced in service layer (`organization_id` access check).
- `payment_status` on orders is architectural; no charge capture endpoint.
- Verification badge values validated against vocabulary; disclaimer always present on seller responses.
