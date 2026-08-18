# Twin — Relationship Diagram

```
TwinObject (permanent UUID)
    │
    ├── FabricPassport (never disappears)
    │       └── FabricRelationship / FabricEvent / Digital Thread API
    │
    ├── TwinHistoryEntry* (immutable append-only)
    │       ownership | configuration | installation | removal |
    │       maintenance | inspection | repair | modification |
    │       sb/ad compliance | llp | utilization | failure |
    │       certificate | document | publication | signature | audit | lifecycle
    │
    ├── TwinConfiguration* (current | previous | future_planned)
    │
    ├── TwinReliabilitySnapshot* (architecture-only metrics)
    │
    └── TwinSearchEntry (1:1 search projection)
```

Digital Thread traversal: prefer `GET /api/v1/fabric/passports/{id}/thread` via twin relationship hint.
