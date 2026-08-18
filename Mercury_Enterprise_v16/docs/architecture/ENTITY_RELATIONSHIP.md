# Entity Relationship Diagram — Universal Data Fabric

```mermaid
erDiagram
  FABRIC_ENTITY_TYPES ||--o{ FABRIC_PASSPORTS : classifies
  FABRIC_PASSPORTS ||--o{ FABRIC_PASSPORT_HISTORY : revises
  FABRIC_PASSPORTS ||--o{ FABRIC_RELATIONSHIPS : from
  FABRIC_PASSPORTS ||--o{ FABRIC_RELATIONSHIPS : to
  FABRIC_PASSPORTS ||--o{ FABRIC_EVENTS : timeline
  FABRIC_PASSPORTS ||--o{ FABRIC_TAGS : tagged
  FABRIC_PASSPORTS ||--o{ FABRIC_ATTACHMENT_REFS : attaches
  FABRIC_PASSPORTS ||--o{ FABRIC_LEGAL_HOLDS : held
  FABRIC_RETENTION_POLICIES ||--o{ FABRIC_PASSPORTS : governs

  FABRIC_PASSPORTS {
    string id PK
    string organization_id
    string entity_type
    string entity_id
    string passport_number
    string lifecycle
    string digital_identity
    int version
  }

  FABRIC_RELATIONSHIPS {
    string id PK
    string from_passport_id
    string to_passport_id
    string relationship_type
    string cardinality
  }

  FABRIC_EVENTS {
    string id PK
    string passport_id
    string event_type
    datetime occurred_at
  }
```

Domain tables (aircraft, work_orders, …) remain external; passports reference them by `(entity_type, entity_id)`.
