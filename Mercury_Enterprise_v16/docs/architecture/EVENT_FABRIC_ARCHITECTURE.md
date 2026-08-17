# Mercury Enterprise Event Fabric — Architecture

**Program 17** · Event-driven nervous system for Mercury AEOS.

## Positioning

The Event Fabric makes important business actions **immutable, versioned, auditable, replayable** enterprise events — without replacing Digital Thread `fabric_events` or the in-memory Event Framework bus.

| Layer | Role |
|-------|------|
| Event Catalog | Versioned PascalCase enterprise types |
| Event Store | Append-only durable log (`enterprise_event_store`) |
| Event Bus | Publish via Event Framework + subscription registry |
| DLQ / Retry | Failed delivery capture and retry |
| Replay | Re-emit stored events to the bus |
| Observability | Actor, tenant, correlation/trace IDs, source/target, severity, duration |

## Separation of concerns

- **`fabric_events`** — Digital Thread / passport timeline (Program 11)
- **`event_framework`** — in-process publish/subscribe (Program A)
- **`enterprise_event_*`** — cross-domain durable Event Fabric (Program 17)

## Package

`backend/app/event_fabric/` → `/api/v1/event-fabric`  
Permissions: `event_fabric.read` / `event_fabric.manage`  
Alembic: `20260814_0020`

## Related docs

- [EVENT_CATALOG.md](EVENT_CATALOG.md)
- [EVENT_FLOW_DIAGRAMS.md](EVENT_FLOW_DIAGRAMS.md)
- [EVENT_FABRIC_API.md](EVENT_FABRIC_API.md)
- [EVENT_FABRIC_FUTURE_ROADMAP.md](EVENT_FABRIC_FUTURE_ROADMAP.md)
- [EVENT_FABRIC_PRODUCTION_READINESS.md](EVENT_FABRIC_PRODUCTION_READINESS.md)
- ADR-0017
