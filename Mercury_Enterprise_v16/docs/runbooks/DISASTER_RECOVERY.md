# Disaster Recovery — Mercury Enterprise V2.0

This runbook matches the current architecture (FastAPI + vanilla JS + SQLite or Postgres via Compose). It is not a multi-region HA design.

## What is durable

- SQL: incidents, timeline events, evidence (+ provenance), `audit_events`
- Compose Postgres volume: `mercury_postgres`

## What is volatile (process memory)

- Sessions
- Approvals
- AlertManager / TimelineManager rings
- Connector health history ring
- Decision evaluation/review store (Task 19 Option A)

## Backup

### Postgres (Compose)

```bash
docker compose exec postgres pg_dump -U mercury mercury > mercury-backup.sql
```

### SQLite

Copy `mercury.db` while the API is stopped (or use a filesystem snapshot).

## Restore

1. Stop backend writers.
2. Restore dump/file to the configured `DATABASE_URL`.
3. Start backend/frontend.
4. Verify `/api/v1/ready`, login, Admin audit, reports.

## RTO / RPO guidance (reference)

| Item | Guidance |
|------|----------|
| RPO | Bound by backup frequency chosen by operators (not automated in-repo) |
| RTO | Typical single-host restart + restore minutes; validate in your environment |
| Decision reviews | Expect re-evaluation after restore/restart unless Option B was approved |

## Failure modes

| Failure | Recovery |
|---------|----------|
| Database unavailable | `/ready` returns 503; fix DB; restart API |
| Backend crash | Restart container/process; sessions/decisions reset |
| Connector outage | Mark degraded; human recover via Integrations |
| Accidental data loss | Restore from last backup; do not invent synthetic audit rows |
