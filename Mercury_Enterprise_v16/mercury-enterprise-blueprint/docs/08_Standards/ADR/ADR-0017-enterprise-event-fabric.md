# ADR-0017 — Mercury Enterprise Event Fabric

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-08-14 |
| Related | ADR-0009, ADR-0010, ADR-0011, ADR-0015 |

## Context

Mercury needs an event-driven enterprise nervous system: immutable, versioned, auditable, replayable events for analytics, AI, and cross-product coordination — without conflating Digital Thread timeline storage or the in-memory bus.

## Decision

1. Introduce `backend/app/event_fabric/` with catalog, store, subscriptions, DLQ, replay.
2. Keep `fabric_events` as Digital Thread entity timeline.
3. Keep `event_framework` as in-process bus; Event Fabric publishes through it.
4. Use PascalCase versioned catalog codes for enterprise semantics.
5. Require tenant isolation + RBAC + audit on fabric APIs.
6. Defer external brokers to Connect-backed adapters.

## Consequences

- Clear path to replace tight coupling with events
- Dual-write migration can proceed product-by-product
- Marketing must not claim Kafka-class broker semantics yet

## EPIC-001 update (2026-08-14)

- Domain → Fabric dual-write is active for types listed in `BUS_TO_CATALOG` via
  `event_framework.publish_sync(..., dual_write=True)` → `maybe_dual_write_to_fabric`.
- Ownership matrix: `docs/architecture/EVENT_OWNERSHIP_MATRIX.md`.
- Fabric → Framework mirrors set `dual_write=False` to prevent recursion.
