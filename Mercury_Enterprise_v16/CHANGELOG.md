# Changelog

All notable changes to Mercury Enterprise are summarized here. Package/API version remains `16.0.0` unless noted; sprint tags mark security/ops increments.

## Sprint 7b — Technical Library, Personnel & Maintenance Certification

### Added
- Expanded publication types (maintenance / flight / engineering / operations) with revision history and library browse
- Aircraft families, alternate parts / interchangeability, personnel qualifications & ACA authorizations
- Maintenance Task Engine (scheduled/unscheduled/corrective/preventive/inspections/checks/troubleshooting/replacement/deferred/MEL-CDL/SB/EO) with library revision binding, certification flags, release → technical logbook, audit trail API
- Critical-task policies, immutable digital signatures, certification chain, technical logbook
- AI-ready index / embedding / cross-ref stubs (no AI compute); enterprise RBAC permission expansion + persona map
- Production-readiness hardening: certify credential + authority/expiry checks, task lifecycle transitions, release→component history, publication activate RBAC fix, library types WDM/SDM/TSM/MFIM, family browse API, pagination
- Alembic `20260813_0005`–`20260813_0008`; docs for publications, library, personnel, tasks, certification, signatures, logbook, RBAC

## Sprint 7 — Aircraft Components & Configuration Management

### Added
- ATA chapters, component catalog, serialized components, immutable installation history
- Install / remove / transfer flows with TSN/CSN/TSO/CSO decimal hour tracking and optional life limits
- Aircraft configuration API; permissions `component.*` / `configuration.*`
- Alembic `20260812_0004_aircraft_components`; docs `docs/AIRCRAFT_CONFIGURATION.md`

## Sprint 6 — Aircraft Registry & Fleet Management

### Added
- Aviation domain: manufacturers, aircraft models, statuses, fleet operators, fleets, aircraft, registrations
- Alembic migration `20260812_0003_aircraft_registry`
- REST APIs under `/api/v1/fleet/*` with org isolation, audit events, and seed catalog/demo fleet
- Permissions `fleet.read` / `fleet.manage`; dashboard `fleet_health.aircraft_online` from registry
- Docs: `docs/FLEET_REGISTRY.md`

## Sprint 5 — Enterprise Organizations & Multi-Tenancy

### Added
- Persisted hierarchy: companies, organizations, sites, departments, teams, org users, memberships
- Alembic migration `20260812_0002_enterprise_organizations`
- REST APIs under `/api/v1/companies|organizations|sites|departments|teams|org/users|memberships|org/me`
- Membership-aware session context (`auth/context`) and org-scoped role resolution
- Idempotent aviation seed (East/West orgs and sites) with operator memberships
- Permissions `org.read` / `org.manage`; docs in `docs/ORGANIZATIONS.md`

### Security
- Context switches denied without organization membership (platform admin exempt)
- Organization list/site APIs filtered by membership

## v0.9.2 — Enterprise Observability & Operations

### Added
- JSON structured logging with request, correlation, and user IDs; optional rotating file logs
- Enriched `/health`, `/ready`, `/live` (database, optional Redis, disk, memory, versions, uptime)
- Prometheus metrics at `/metrics` and admin JSON snapshot at `/admin/metrics`
- Administrator APIs: `/admin/system`, `/admin/health`, `/admin/metrics`, `/admin/audit`
- Expanded audit actions (login failure, user/password/role/config changes, optional API access)
- Hashed in-memory operator directory with admin user management endpoints
- Backup scripts: `scripts/backup_database.sh`, `restore_database.sh`, `verify_backup.sh`
- Docs: `docs/OBSERVABILITY.md`, `AUDIT_LOGGING.md`, `BACKUP.md`, `MONITORING.md`

### Security
- Rate-limit blocks metered without request-path DB writes under flood
- API-access audit opt-in (`MERCURY_AUDIT_API_ACCESS`, default off)
- Last-Administrator demotion blocked

## v0.9.1 — Production Security & Infrastructure

### Added
- Edge NGINX HTTPS (TLS 1.2/1.3, Let's Encrypt, HTTP→HTTPS redirect)
- Security headers, reverse-proxy WS/gzip/timeouts/upload limits
- Application + NGINX rate limiting (HTTP 429)
- Compose production profile (`nginx`, `certbot`), healthchecks, restart policies
- Root probes `/health`, `/ready`, `/live`
- `docs/security/HTTPS.md`, production env validation (`JWT_SECRET`, `COOKIE_SECRET`, …)

## 16.0.0 — Mercury Enterprise V2.0

### Added
- Production-oriented FastAPI lifespan and configuration
- PostgreSQL Docker deployment with persistent volume
- NGINX frontend/reverse proxy
- WebSocket live event gateway and heartbeat
- Health and readiness probes
- Session RBAC, audit, decisions, connectors, reporting
- Request IDs, structured logging, generic error responses
- GitHub Actions CI
- Architecture, security, and production-readiness guides

### Retained
- Full Mercury simulated enterprise command workspaces and operational demonstration features

### Limitation
- Not certified or approved for real aviation, defence, surveillance, emergency-response, or safety operations

## 15.0.0

### Added
- Production-oriented FastAPI lifespan and configuration
- PostgreSQL Docker deployment with persistent volume
- NGINX frontend/reverse proxy
- WebSocket live event gateway and heartbeat
- Health and readiness probes
- Optional API-key protection for write endpoints
- Request IDs, response timing, structured logging, and generic error responses
- GitHub Actions CI
- Architecture, security, and production-readiness guides

### Retained
- Full Mercury simulated enterprise command workspaces and operational demonstration features

### Limitation
- Not certified or approved for real aviation, defence, surveillance, emergency-response, or safety operations
