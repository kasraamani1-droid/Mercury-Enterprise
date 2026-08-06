# Production Readiness Checklist

This release is a reference platform, not an operational approval.

## Included
- health/readiness probes
- environment configuration
- PostgreSQL deployment option
- persistent database volume
- WebSocket event gateway
- API write protection baseline
- structured logs and request IDs
- CI workflow and tests
- NGINX reverse proxy

## Mandatory before operational use
- replace all simulated feeds with validated adapters
- define data ownership, provenance, quality, and fail-safe behavior
- establish SLOs, backup/restore, RTO/RPO, monitoring, and alerting
- conduct penetration, load, resilience, accessibility, and human-factors testing
- implement full identity, authorization, audit, evidence-chain, and privacy controls
- complete legal, regulatory, safety, and certification reviews
- create operator training and approved standard operating procedures
