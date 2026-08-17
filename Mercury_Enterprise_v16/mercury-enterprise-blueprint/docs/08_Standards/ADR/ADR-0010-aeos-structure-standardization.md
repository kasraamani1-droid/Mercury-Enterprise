# ADR-0010 — AEOS structure standardization without big-bang moves

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-08-14 |
| Deciders | CTO / Lead Architect |
| Related | ADR-0001, ADR-0004, ADR-0009 |

## Context

Mercury must present a Dynamics/SAP-class platform structure while the running system is a working modular monolith with many imported paths, tests, and UI contracts. A physical re-tree of every package would break imports and delay product delivery.

## Decision

1. **Logical AEOS architecture is canonical** (documented in `docs/architecture/`).
2. **Physical moves are deferred**; packages keep stable paths (`org`, `fleet`, `logistics`, …).
3. **Shared services are mandatory facades** under `platform/` + `shared/` (audit engine, permission service, event framework, integration framework, workflow bridge).
4. **Readiness domains** (marketplace, oem, authority) ship as real tables/APIs decoupled from maintenance.
5. **Workflow**: operational modules resolve transitions from the generic engine; job cards are the first migrated consumer.

## Consequences

- Stable APIs and tests during AEOS expansion
- Clear ownership map for every future product
- Residual debt: some domain status machines still local until bridged
- Folder tree will converge later via aliases/re-exports, not rewrite

## Alternatives rejected

- Big-bang rename to `backend/platform/identity/...` — too disruptive
- Separate microservice per platform service now — premature without shared session/event bus
