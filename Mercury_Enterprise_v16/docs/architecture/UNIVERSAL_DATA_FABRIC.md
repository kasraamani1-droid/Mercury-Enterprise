# Universal Data Fabric — Architecture Summary (Program 11)

Mercury’s **Universal Data Fabric** is the enterprise knowledge-graph substrate over the modular monolith’s relational domain tables. It does **not** replace fleet, logistics, or work-order schemas. It issues a **Digital Passport** for every object and connects passports with typed relationships, timeline events, tags, attachments, search, and governance.

## Layers

```
Domain tables (aircraft, WO, stock, …)
        │  entity_type + entity_id
        ▼
Digital Passport (fabric_passports)
        │
        ├─ Relationships (fabric_relationships)  ← Knowledge Graph edges
        ├─ Events (fabric_events)                ← Enterprise timeline
        ├─ History (fabric_passport_history)
        ├─ Tags / Attachments
        └─ Governance (retention, legal hold)
                │
                ▼
Platform Search (ai_metadata_json) + Event Framework
```

## Package

| Path | Role |
|------|------|
| `backend/app/fabric/` | Universal Entity Model runtime |
| `/api/v1/fabric/*` | REST API |
| Alembic `20260814_0014` | Schema |

## Universal entity attributes

Every passport carries: UUID, tenant (`organization_id`), created/modified, soft delete, audit (via AuditEngine), lifecycle, permissions hint, relationships, tags, attachments, history, digital identity (`did:mercury:…`), AI metadata.

## Compatibility

Additive only. Existing domain APIs unchanged. Domains optionally call `FabricService.ensure_passport` / `emit_event` / `link` as they mature.

## Related docs

- [DIGITAL_THREAD.md](DIGITAL_THREAD.md)
- [DIGITAL_PASSPORT.md](DIGITAL_PASSPORT.md)
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md)
- [KNOWLEDGE_GRAPH.md](KNOWLEDGE_GRAPH.md)
- [ENTITY_RELATIONSHIP.md](ENTITY_RELATIONSHIP.md)
