# Production Readiness Checklist

This release is an **engineering Release Candidate / reference platform**, not an operational certification or weapons-system approval.

## Provided in Milestone 2 RC

- Health / readiness probes with subsystem checks (`/api/v1/health`, `/api/v1/ready`)
- Platform and ops diagnostics (`/api/v1/platform/status`, `/api/v1/ops/health`)
- Request IDs and request timing headers; request logging
- Optional JSON logging (`MERCURY_LOG_JSON`)
- Environment configuration (`MERCURY_*`, `DATABASE_URL`)
- PostgreSQL deployment option via Docker Compose + persistent volume
- WebSocket event gateway
- Session auth, RBAC, org/site scoping
- Durable audit events and evidence provenance
- Historical reporting APIs
- Connector lifecycle controls (human start/stop/recover)
- Advisory decision explainability and human review APIs/UI
- CI workflow (pytest, compileall, node syntax checks, compose config best-effort)
- NGINX reverse proxy foundations
- Operator/administrator/deploy/DR runbooks under `docs/runbooks/`

## Still required before live operational use

- Replace simulated feeds with validated production adapters
- Define SLOs, monitoring/alerting integrations, and on-call ownership
- Establish tested backup/restore cadence with measured RTO/RPO
- Penetration, load, resilience, accessibility, and human-factors testing
- Full identity provider integration (beyond demo credentials)
- Legal, regulatory, safety, and certification reviews
- Formal operator training and approved SOPs beyond these runbooks
- Confirm `MERCURY_SESSION_COOKIE_SECURE=true` and TLS termination in production

## Human-control invariant

No resilience, observability, recovery, or explainability feature may imply autonomous operational authority.
