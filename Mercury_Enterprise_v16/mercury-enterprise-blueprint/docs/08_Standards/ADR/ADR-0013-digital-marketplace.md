# ADR-0013 — Mercury Digital Marketplace

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-08-14 |
| Related | ADR-0001, ADR-0008, ADR-0009, ADR-0010, ADR-0011, ADR-0012 |

## Context

Mercury must host a global B2B aviation commerce platform for parts, rotables, tools, calibration, repairs, training, publications, software, jobs, and consulting — without becoming an inventory owner or claiming regulatory verification.

## Decision

1. Expand the existing `marketplace` package (do not fork a second commerce domain).
2. Introduce seller profiles, products, cart, quotes, orders/lines, reviews, favorites, saved searches.
3. Retain legacy `marketplace_listings` for backward compatibility.
4. Treat verification badges and payment status as **architecture readiness only**.
5. Store AI recommendation/ranking/alternate hooks in `ai_metadata_json` without executing LLMs.
6. Reuse AuditEngine, Event Framework, Fabric entity types, and Ecosystem marketplace enrollment.

## Consequences

- Clear path to the world’s largest aviation digital marketplace inside AEOS
- Marketing/compliance must keep badge and payment disclaimers
- Future payment/shipping/document-verification adapters plug via Connect
- Cross-tenant public catalog remains a deliberate follow-on decision
