# Event Fabric — Flow Diagrams

## Publish sequence

```
Producer Service
    → EventFabricService.publish (validate catalog + version)
    → Append enterprise_event_store (immutable)
    → Match enterprise_event_subscriptions
    → event_framework.publish_sync (in-process bus)
    → AuditEngine
```

## Failure / DLQ

```
Handler failure (simulated or reported)
    → POST /dlq (status=open, store marked dead_lettered)
    → POST /dlq/{id}/retry
    → Re-publish to bus + status=retried / delivered
```

## Replay

```
POST /replay (filter by code / time window)
    → Load store events chronologically
    → Re-publish with payload.replay=true
    → Record enterprise_event_replays job
```

## Domain dual-write (target end state)

```
Domain mutation commit
    → Domain-specific persistence
    → Event Fabric publish (catalog code)
    → Optional Fabric.emit_event (Digital Thread)
```
