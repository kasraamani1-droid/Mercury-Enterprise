# Implementation Status — Mercury Enterprise v15.0 Foundation

This repository is a working **production-oriented foundation**, not a finished certified airport-security product.

## Implemented and runnable

- FastAPI REST API for incidents, timeline events, evidence, reports, health and readiness
- SQLAlchemy persistence with SQLite local mode and PostgreSQL Docker mode
- WebSocket gateway with heartbeat and incident broadcasts
- Optional API-key protection for write operations
- Modular browser frontend with command, radar, digital-twin-style, executive, history, admin, cloud, integrations and compliance views
- Dockerfiles, Docker Compose, NGINX reverse-proxy reference configuration
- Automated backend tests and CI workflow
- Windows startup, check and stop scripts

## Demonstration/simulated only

- UAV and aircraft tracks
- Radar, RF, EO and thermal sensor feeds
- AI threat assessment and Copilot outputs
- Weather, compliance, readiness and integration data
- Digital twin visuals and operational recommendations

## Not yet implemented as production integrations

- Certified radar/RF/camera hardware adapters
- ADS-B or airport operational-data licensing and feeds
- Enterprise SSO/OIDC and full RBAC policy engine
- Immutable evidence vault and signed audit ledger
- Safety case, regulatory approval, cybersecurity accreditation and human-factors validation
- High-availability Kubernetes deployment proven under load

Use this codebase as a deployable engineering foundation and demonstration environment. Do not use it for operational safety or security decisions without independent validation and authorized integrations.
