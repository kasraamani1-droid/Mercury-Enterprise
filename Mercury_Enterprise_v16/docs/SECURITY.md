# Security Baseline

Included:
- explicit CORS origins
- session-cookie authentication with server-side RBAC
- site/org scoping on incident list/detail reads
- **required** `MERCURY_AUTH_PASSWORD` (no embedded demo/default; forbidden values rejected at startup)
- interactive operator sign-in (no demo auto-login)
- production Secure cookie default when `MERCURY_ENV=production`
- request IDs and generic 500 responses
- NGINX security headers
- environment-based secrets (`.env` / `MERCURY_*`)

Not currently enforced (reserved / deferred):
- `MERCURY_API_KEY` is configuration-only; session RBAC is the active control plane
- OIDC/SSO/MFA

Public probes: `GET /health`, `GET /ready`, `GET /live` (also `/api/v1/health`, `/api/v1/ready`).
Metrics: `GET /metrics` (Prometheus). Admin ops: `GET /admin/system|health|metrics|audit`.

HTTPS / TLS production deployment: `docs/security/HTTPS.md`.
Observability: `docs/OBSERVABILITY.md`, `docs/AUDIT_LOGGING.md`, `docs/MONITORING.md`, `docs/BACKUP.md`.

See `docs/design/PRODUCTION_HARDENING_REPORT.md` and `.env.example`.
