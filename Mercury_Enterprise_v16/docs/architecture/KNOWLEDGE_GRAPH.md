# Knowledge Graph Vision

Mercury’s graph is **not** a separate graph database in this release. It is an **Enterprise Knowledge Graph projection** over:

1. Relational domain tables (source of truth)
2. Fabric passports (stable node IDs)
3. Fabric relationships (typed edges)
4. Fabric events (temporal facts)

## Why this shape

- Aviation needs ACID writes for airworthiness evidence (SQL).
- Cross-product questions need graph traversal (passports + edges).
- Future OpenSearch / vector / twin layers consume passport AI metadata without rewriting domains.

## Future

- Materialized graph views / Neo4j or Neptune export adapters
- Semantic search over passport embeddings (`embedding_ready` flag today)
- Digital Twin simulation subscribed to fabric events
- Cross-tenant marketplace edges under explicit governance

## Non-goals (now)

- Replacing PostgreSQL/SQLite with a graph DB
- Building LLM features
