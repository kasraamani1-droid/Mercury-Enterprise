# Observability

Mercury exposes structured logs, health probes, Prometheus metrics, and admin operations APIs for enterprise operations.

## Structured logging

Enable JSON logs:

```env
MERCURY_LOG_JSON=true
LOG_LEVEL=INFO
LOG_FILE=/var/log/mercury/api.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
```

Each log line includes:

| Field | Source |
|-------|--------|
| `level` | `LOG_LEVEL` |
| `request_id` | `X-Request-ID` (generated if absent) |
| `correlation_id` | `X-Correlation-ID` (falls back to request id) |
| `user_id` | Authenticated operator when a session cookie is present |

Responses echo `X-Request-ID` and `X-Correlation-ID`. File logging uses rotating handlers when `LOG_FILE` is set.

## Health probes

| Endpoint | Purpose |
|----------|---------|
| `GET /live` | Process liveness |
| `GET /ready` | Readiness (database required; Redis only if `REDIS_REQUIRED=true`) |
| `GET /health` | Detailed health |

`/health` includes database, Redis (`ok` / `error` / `not_configured`), disk, memory, API version, build version, and uptime. Compatibility probes remain at `/api/v1/health` and `/api/v1/ready`.

## Metrics

Prometheus exposition:

```http
GET /metrics
```

Controlled by `MERCURY_METRICS_ENABLED` (default `true`). Tracks request rates/latency/errors, login attempts/failures, active users, and database latency.

Admin JSON snapshot:

```http
GET /admin/metrics
```

## Admin operations

Administrator session required:

- `GET /admin/system`
- `GET /admin/health`
- `GET /admin/metrics`
- `GET /admin/audit`

See `docs/MONITORING.md` and `docs/AUDIT_LOGGING.md`.
