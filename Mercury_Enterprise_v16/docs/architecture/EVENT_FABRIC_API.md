# Event Fabric API

Base: `/api/v1/event-fabric`

| Area | Methods | Paths |
|------|---------|-------|
| Overview | GET | `/overview` |
| Catalog | GET | `/catalog` |
| Events | POST, GET, GET | `/events`, `/events/{event_id}` |
| Subscriptions | GET, POST | `/subscriptions` |
| DLQ | GET, POST, POST | `/dlq`, `/dlq/{id}/retry` |
| Replay | POST | `/replay` |

Every stored event includes timestamp, actor, tenant (`organization_id`), correlation_id, trace_id, source_service, target_service, severity, status, duration_ms.
