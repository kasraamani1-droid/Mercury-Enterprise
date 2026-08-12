# Changelog

All notable changes to Mercury Enterprise are summarized here. Package/API version remains `16.0.0` unless noted; sprint tags mark security/ops increments.

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
