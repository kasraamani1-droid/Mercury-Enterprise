# ADR-0014 — Mercury Aviation Network

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-08-14 |
| Related | ADR-0001, ADR-0003, ADR-0009, ADR-0010, ADR-0011, ADR-0012, ADR-0013 |

## Context

Mercury must enable enterprise aviation collaboration across airlines, MROs, OEMs, suppliers, authorities, training orgs, and more — without becoming social media and without weakening tenant isolation.

## Decision

1. Introduce `backend/app/network/` as the Aviation Network domain.
2. Keep organizations isolated by default.
3. Require **explicit active partnerships** (with permission scopes) before cross-org collaboration, messaging, or document sharing.
4. Provide org + professional profiles, directory projection, events, and audited workflows.
5. Treat certificates/approvals/authority relationships as architecture readiness — not regulatory claims.

## Consequences

- Clear security boundary for multi-org work
- Marketplace / Fabric / Ecosystem remain complementary (commerce, identity, stakeholder maps)
- Future federated directory and encryption adapters plug into this model
- Product copy must retain “not social media / not regulatory verification” language
