# Event Ownership Matrix (EPIC-001)

**Status:** Active for Platform 1.0 RC  
**Related:** ADR-0017, `EVENT_FABRIC_ARCHITECTURE.md`, `event_fabric/catalog.py`

## Layers

| Layer | Package | Durability | Purpose |
|-------|---------|------------|---------|
| **Event Framework** | `platform/event_framework.py` (+ shim `events/bus.py`) | In-process history | Canonical dotted bus types for domain publishers & connectors |
| **Core bus** | `core/event_bus.py` | In-process | Mission / ops / decision subscribers |
| **Enterprise Event Fabric** | `event_fabric/` | DB store + subscriptions + DLQ | Durable enterprise catalog events (PascalCase codes) |
| **Digital Thread** | `fabric/` (`fabric_events`) | DB | Entity passport / relationship timeline (not the enterprise catalog) |

## Dual-write policy (domain → Fabric)

1. Domains emit **dotted** types via `event_framework.publish_sync(...)`.
2. When `organization_id` is set and the type appears in `BUS_TO_CATALOG`, Mercury **best-effort** dual-writes into Event Fabric (`maybe_dual_write_to_fabric`).
3. Failures are logged; domain commits are **not** rolled back.
4. Fabric → Framework mirrors pass `dual_write=False` to prevent recursion.

### Mapped types (RC)

| Bus type | Catalog code |
|----------|--------------|
| `twin.created` / `twin.updated` | TwinCreated / TwinUpdated |
| `marketplace.*.created` (seller/product/listing/quote/order) | SupplierRegistered / ProductPublished / QuoteRequested / OrderCreated |
| `fabric.passport.created` / `fabric.relationship.created` | PassportUpdated / RelationshipCreated |
| `plugins.installed` | OrganizationUpdated |
| `fleet.aircraft.created` | AircraftCreated |
| `work_order.created` | WorkOrderCreated |

Unmapped bus types remain Framework-only until explicitly added to `BUS_TO_CATALOG`.

## Ownership rules

- **Do not** invent a second bus for RC.
- Digital Thread events stay on Fabric Thread tables unless also published on the Framework with an intentional mapping.
- Brokers (Kafka/NATS) remain out of scope (ADR-0017).
