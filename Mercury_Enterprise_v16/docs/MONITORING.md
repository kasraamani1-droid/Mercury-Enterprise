# Monitoring

## Probe map

| Probe | Auth | Failure mode |
|-------|------|--------------|
| `GET /live` | none | process down |
| `GET /ready` | none | HTTP 503 if database (or required Redis) unavailable |
| `GET /health` | none | `status=degraded` when dependencies unhealthy |
| `GET /metrics` | none | Prometheus text exposition |
| `GET /admin/health` | Administrator | Full health payload |
| `GET /admin/metrics` | Administrator | JSON counters/gauges |
| `GET /admin/system` | Administrator | Runtime/system summary |
| `GET /admin/audit` | Administrator | Cross-site audit feed |

## Prometheus scrape example

```yaml
scrape_configs:
  - job_name: mercury-api
    metrics_path: /metrics
    static_configs:
      - targets: ["backend:8000"]
```

Key series:

- `mercury_http_requests_total`
- `mercury_http_request_duration_seconds`
- `mercury_http_errors_total`
- `mercury_login_attempts_total{outcome="success|failure"}`
- `mercury_rate_limit_blocks_total`
- `mercury_active_users`
- `mercury_database_latency_seconds`

Keep `/metrics` on the Compose network only (backend is not published on the host in production). Do not expose it through the public edge NGINX without an authenticated scrape gateway.

## Redis

Redis is optional. Set `REDIS_URL` to enable connectivity checks. Set `REDIS_REQUIRED=true` only when readiness must fail closed without Redis. When unset, health reports `redis=not_configured`.

## Suggested alerts

1. `/ready` failing for > 1 minute
2. Error rate (`mercury_http_errors_total`) spike
3. Login failure burst (`outcome="failure"`)
4. Disk/memory `degraded` on `/health`
5. Backup verification job failed (see `docs/BACKUP.md`)
