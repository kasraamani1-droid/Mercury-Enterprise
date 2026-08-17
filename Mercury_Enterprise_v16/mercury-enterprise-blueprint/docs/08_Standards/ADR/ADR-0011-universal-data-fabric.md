# ADR-0011 — Universal Data Fabric as Digital Thread substrate

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-08-14 |
| Related | ADR-0001, ADR-0002, ADR-0009, ADR-0010 |

## Context

Mercury products need one Digital Thread and Digital Passports without rewriting every domain table into a single mega-schema or adopting a graph database prematurely.

## Decision

1. Introduce `backend/app/fabric/` as the **Universal Data Fabric**.
2. Every object gains a **Digital Passport** keyed by `(organization_id, entity_type, entity_id)`.
3. Relationships, events, tags, attachments, history, and governance live in fabric tables.
4. Domain tables remain authoritative for business fields; fabric is the cross-product join spine.
5. Search/AI readiness flows through passport + `ai_metadata_json` mirrored to platform search.
6. Knowledge Graph is a projection over fabric edges — not a separate DB in this release.

## Consequences

- Digital Thread queries become first-class (`/thread`)
- Incremental adoption by domains without breaking APIs
- Dual-write discipline required as modules emit fabric events
- Graph DB export remains a future adapter
