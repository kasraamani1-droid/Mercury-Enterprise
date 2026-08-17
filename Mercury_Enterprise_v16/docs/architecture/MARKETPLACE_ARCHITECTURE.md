# Mercury Digital Marketplace — Architecture

**Program 13** · B2B aviation commerce platform integrated into Mercury AEOS.

## Positioning

Mercury Marketplace is **not** an online store. It is a multi-tenant B2B commerce layer where:

- Mercury owns the **platform** (catalog engine, quotes, orders, search, reviews).
- Organizations own **inventory and offerings**.
- Every approved organization can become a **seller**.
- Buyers include operators, airlines, bizav, MRO, OEM, government, training orgs (military future).

## Design principles

1. **Additive** to existing `backend/app/marketplace/` (legacy listings retained).
2. **Tenant isolation** via org-scoped service queries + RBAC (`marketplace.read` / `marketplace.manage`).
3. **Verification badges** are platform readiness markers only — **not** regulatory verification.
4. **Payment gateway** is future-ready (`payment_status=not_configured`); no live PSP.
5. **AI-ready metadata** only (recommendations / ranking / alternates flags) — no LLM execution.

## Package layout

| Module | Role |
|--------|------|
| `catalog.py` | Categories, seller/buyer types, badge vocab, statuses |
| `models.py` | Sellers, products, cart, quotes, orders, reviews, favorites, saved searches + legacy listings |
| `service.py` | Commerce workflows, audit, events |
| `router.py` | REST `/api/v1/marketplace/*` |
| `schemas.py` | API contracts |

## Catalog families

Aircraft parts, rotables, consumables, expendables, special tools, GSE, test equipment, calibration, component/engine/avionics repairs, engineering/painting/interior/NDT services, training, publications, software, jobs, consulting.

## Seller model

Digital profile with type (OEM, distributor, PMA, AMO, repair station, cal lab, training org, engineering, software, tool mfr, parts supplier, consultant), capabilities, certificates/approvals JSON, locations, ratings, turnaround, and architecture-only verification badges.

## Commerce engine

Catalog → Search/Filter → Favorites / Saved searches → Cart → Quote → Order (lines) → Reviews. Shipping and invoice refs are structured fields; fulfillment adapters remain Connect-ready.

## Integration

- **Fabric**: entity types `marketplace_seller`, `marketplace_product`, `marketplace_order`, `marketplace_quote`.
- **Ecosystem**: marketplace stakeholder capabilities updated for quotes/orders/reviews.
- **Events**: `marketplace.*.created` via Event Framework.
- **Audit**: fail-closed AuditEngine on create paths.

## Related docs

- [MARKETPLACE_BUSINESS_MODEL.md](MARKETPLACE_BUSINESS_MODEL.md)
- [MARKETPLACE_ENTITY_RELATIONSHIP.md](MARKETPLACE_ENTITY_RELATIONSHIP.md)
- [MARKETPLACE_WORKFLOW.md](MARKETPLACE_WORKFLOW.md)
- [MARKETPLACE_API.md](MARKETPLACE_API.md)
- [MARKETPLACE_PRODUCTION_READINESS.md](MARKETPLACE_PRODUCTION_READINESS.md)
- ADR-0013
