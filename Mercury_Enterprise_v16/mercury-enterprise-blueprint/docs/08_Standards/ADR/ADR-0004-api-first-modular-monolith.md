# ADR-0004 — API-first modular monolith; extract services only when justified

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-08-14 |
| Deciders | Lead architect, principal engineer, product leadership |
| Affects | [Technical Architecture](../../02_Architecture/Technical_Architecture.md) · [Domain Architecture](../../02_Architecture/Domain_Architecture.md) · [API Standards](../API_Standards.md) · [Coding Standards](../Coding_Standards.md) · [ADR-0005](ADR-0005-vanilla-js-fastapi-stack.md) |
| Supersedes | Informal “microservices later” discussions |
| Superseded by | — |

---

## Context

Mercury spans organizations, fleets, components, publications, personnel, certification, work orders, planning, and logistics. That breadth tempts a services-per-domain topology early.

The counter-forces are equally strong:

1. **Airworthiness transactions are cross-domain.** Certify → logbook → configuration history → audit must commit together. Distributed sagas replace that atomicity with eventual consistency — unacceptable for release evidence.
2. **The domain is still moving.** Boundaries drawn into network calls today become expensive to redraw when CAMO, lessor, and OEM packs harden.
3. **A small elite team must ship AEOS capability.** Operational complexity of many services is a safety and delivery risk, not a sophistication badge.
4. **API-first does not require microservices.** Versioned HTTP contracts can front a modular monolith with clear package seams.

The internal module pattern (repository → service → thin router) is specified in [Coding Standards](../Coding_Standards.md) and recorded historically as the layering companion to this ADR (see legacy slug `ADR-0004-repository-service-router.md`).

---

## Decision

**Ship Mercury AEOS as an API-first modular monolith:** one FastAPI deployable, one primary relational database, domain packages with enforced layering and organization isolation. **Extract independently deployable services only when** a domain demonstrates independent scale, independent release cadence, or a hard regulatory isolation requirement that the monolith cannot meet.

Specifically:

| Rule | Requirement |
|------|-------------|
| Contracts | All capabilities exposed under `/api/v1/...` with OpenAPI generated from code |
| Modules | One package per bounded context (`org`, `fleet`, `components`, `publications`, `personnel`, `maintenance`, `work_orders`, `planning`, `logistics`, …) |
| Layering | Router thin; service owns rules/RBAC/audit; repository owns queries |
| Transactions | Prefer single-database transactions for certification and stock ledgers |
| Extraction | Requires a superseding ADR naming the domain, the failure mode of the monolith, and the consistency model replacing local transactions |

---

## Consequences

### Positive

- Atomic Digital Thread writes remain possible.
- Engineers navigate one codebase with clear package boundaries.
- OpenAPI remains the enterprise integration surface for OEMs, MROs, and partners.
- Extraction seams exist without paying distributed-system tax today.

### Negative / accepted costs

- One blast radius for process and database — mitigated by modularity, backups, and observability.
- Nested commits between collaborating modules remain a known debt until transaction bridges mature.
- Teams must resist “new service for every feature” fashion.

### Rejected alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Microservices-first | Premature distribution; certification atomicity becomes saga theatre |
| Big-bang rewrite to event-sourced services | Violates additive architecture rule; destroys working evidence paths |
| Backend-for-frontend without public API discipline | Breaks OEM/partner integration and AEOS positioning |

---

## Links

[ADR-0001](ADR-0001-aeos-not-point-mro.md) · [ADR-0005](ADR-0005-vanilla-js-fastapi-stack.md) · [ADR-0003](ADR-0003-multi-tenant-org-isolation.md) · [Technical Architecture](../../02_Architecture/Technical_Architecture.md) · [API Standards](../API_Standards.md)
