# Implementation Status — Mercury Enterprise V2.0 (package 16.0.0)

This repository is a working **production-oriented foundation**, not a finished certified airport-security product.

**Release identity:** product **Mercury Enterprise V2.0**, package/API `16.0.0` (APPLY_TASK through Task 20 + production hardening).

## Implemented and runnable

- FastAPI REST API for incidents, timeline events, evidence, reports, health and readiness
- SQLAlchemy persistence with SQLite local mode and PostgreSQL Docker mode (+ Alembic baseline)
- WebSocket gateway with heartbeat and incident broadcasts
- Session authentication with role-based permissions (RBAC); password from environment only
- Modular browser frontend with command, radar, digital-twin-style, executive, history, admin, cloud, integrations and compliance views
- Audit logging, evidence provenance, historical reporting, connector lifecycle, decision explainability/review
- Dockerfiles, Docker Compose, NGINX reverse-proxy reference configuration
- Automated backend tests and git-root CI workflow
- Windows startup, check and stop scripts
- Operator/administrator/deploy/DR runbooks under `docs/runbooks/`

## Demonstration/simulated only

- UAV and aircraft tracks
- Radar, RF, EO and thermal sensor feeds
- AI threat assessment and Copilot outputs
- Weather, compliance, readiness and integration data
- Digital twin visuals and operational recommendations

## Not yet implemented as production integrations

- Certified radar/RF/camera hardware adapters
- ADS-B or airport operational-data licensing and feeds
- Enterprise SSO/OIDC and full multi-tenant write scoping on every path
- Immutable evidence vault and signed audit ledger
- Safety case, regulatory approval, cybersecurity accreditation and human-factors validation
- High-availability Kubernetes deployment proven under load
- Enforced API-key middleware (`MERCURY_API_KEY` is reserved only)

Use this codebase as a deployable engineering foundation and demonstration environment. Do not use it for operational safety or security decisions without independent validation and authorized integrations.

See `docs/RELEASE_NOTES_v2.0.md` and `docs/design/FINAL_RELEASE_VERIFICATION_v2.md`.
