# Administrator Runbook — Mercury Enterprise V2.0

## Deployment health verification

```text
GET /api/v1/health
GET /api/v1/ready
GET /api/v1/platform/status
GET /api/v1/ops/health
```

Expect:
- `/ready` → `ready: true` when database is reachable
- `/health` includes `connectors`, `decision_support.advisory_only`, and `checks`
- No secrets in health payloads

## Authentication and RBAC

- Demo operators: `admin`, `operator`, `reviewer`, `viewer` with configured demo password.
- Production: set `MERCURY_AUTH_PASSWORD`, enable `MERCURY_SESSION_COOKIE_SECURE=true` behind TLS.
- Permissions: `decisions.read`, `decisions.review`, `audit.read`, `reports.read`, `connectors.*`.

## Connector diagnosis

1. Open Integrations workspace.
2. Use list/health/health-history APIs.
3. Human lifecycle: start / stop / recover (audited).
4. Degraded connectors must not auto-recover missions or decisions.

## Audit review

- `GET /api/v1/audit` (Reviewer/Admin)
- Confirm decision, connector, incident, and auth actions are attributed with org/site.

## Logging

- Default text logs include method/path/status/request_id/duration.
- Optional JSON logs: `MERCURY_LOG_JSON=true`.
- Never log credentials or full session cookies.

## Maintenance interventions

- Prefer additive config changes via environment variables.
- Restart backend to clear in-memory decision store and connector health rings.
- Durable data remains in SQLite/Postgres (`audit_events`, incidents, evidence).
