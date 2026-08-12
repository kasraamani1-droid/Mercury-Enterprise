# Security

## Baseline controls

| Control | Behavior |
|---------|----------|
| Authentication | Session cookie (`HttpOnly`, `SameSite=Lax`, `Secure` in production/HTTPS) |
| Authorization | Server-side RBAC (Administrator / Operator / Reviewer / Viewer) |
| Secrets | `MERCURY_AUTH_PASSWORD`, `JWT_SECRET`, `COOKIE_SECRET` required in production/HTTPS — no insecure defaults |
| CORS | Explicit origin allow-list |
| Transport | Edge NGINX TLS 1.2+ / 1.3, HTTP→HTTPS redirect (production profile) |
| Headers | HSTS, CSP, frame/options, COOP, CORP, Permissions-Policy |
| Rate limits | Login + `/api/*` → HTTP 429 (NGINX + application) |
| Errors | Generic 500 bodies; request/correlation IDs on responses |
| Operators | In-memory directory; passwords stored hashed (pepper + SHA-256) |

## Public vs protected surfaces

**Public**

- `GET /health`, `/ready`, `/live`
- `GET /api/v1/health`, `/api/v1/ready`
- `GET /metrics` (keep on internal Compose network)

**Administrator only**

- `GET /admin/system`, `/admin/health`, `/admin/metrics`, `/admin/audit`
- Admin user/password/role/config mutations

**Session RBAC**

- Incidents, decisions, reports, connectors, ops, dashboard, etc.

## Deferred (not in this release)

- OIDC / Azure AD / SSO / MFA
- Enforced API-key middleware (`MERCURY_API_KEY` reserved only)
- Multi-worker shared session store (Redis)
- Kubernetes network policies / service mesh

## Operational references

- TLS deployment: [docs/security/HTTPS.md](docs/security/HTTPS.md)
- Audit logging: [docs/AUDIT_LOGGING.md](docs/AUDIT_LOGGING.md)
- Monitoring: [docs/MONITORING.md](docs/MONITORING.md)
- Hardening design history: `docs/design/PRODUCTION_HARDENING_SPEC.md`

## Reporting

Do not commit secrets. Rotate any credential that appears in logs, tickets, or chat. Prefer private disclosure for vulnerabilities.
