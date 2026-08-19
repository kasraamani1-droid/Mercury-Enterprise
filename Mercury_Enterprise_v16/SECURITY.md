# Security

## Baseline controls

| Control | Behavior |
|---------|----------|
| Authentication | Session cookie (`HttpOnly`, `SameSite=Lax`, `Secure` in production/HTTPS). Optional **OIDC authorization-code + PKCE** when configured. JWT access/refresh tokens are **not** used for operator sessions. See [docs/engineering/AUTHENTICATION.md](docs/engineering/AUTHENTICATION.md) |
| Session store | In-memory by default; **Redis** when `REDIS_URL` is set (multi-worker ready). Production OIDC PKCE/state requires Redis (no memory fallback) |
| Machine auth | Optional `MERCURY_API_KEY` via `X-API-Key` or `Authorization: Bearer` (constant-time compare) |
| Authorization | Server-side RBAC (Administrator / Operator / Reviewer / Viewer) |
| Tenant isolation | `assert_org_access` / org-scoped queries; incident writes via `_get_scoped_incident`; WebSocket incident fan-out is org/site scoped. See [docs/engineering/TENANT_ISOLATION.md](docs/engineering/TENANT_ISOLATION.md); suites `test_epic009_security.py`, `test_rc1_tenant_isolation.py` |
| Approvals | Durable SQL `approval_requests` (org/site scoped); audit on request/approve/consume — see [docs/engineering/APPROVAL_PERSISTENCE.md](docs/engineering/APPROVAL_PERSISTENCE.md) |
| Secrets | `MERCURY_AUTH_PASSWORD`, `JWT_SECRET`, `COOKIE_SECRET` required in production/HTTPS — no insecure defaults. `JWT_SECRET` is a production secret / legacy hash pepper, **not** a session JWT signer |
| CORS | Explicit origin allow-list |
| Transport | Edge NGINX TLS 1.2+ / 1.3, HTTP→HTTPS redirect (production profile) |
| Headers | HSTS, CSP, frame/options, COOP, CORP, Permissions-Policy |
| Rate limits | Login + `/api/*` → HTTP 429 (NGINX + application) |
| Errors | Generic 500 bodies; request/correlation IDs on responses |
| Operators | SQL `org_users` directory (hydrated at startup); passwords **Argon2id** with unique salts; legacy SHA-256 verified then rehashed; password reset revokes operator sessions |

## Public vs protected surfaces

**Public**

- `GET /health`, `/ready`, `/live`
- `GET /api/v1/health`, `/api/v1/ready`
- `GET /metrics` (keep on internal Compose network)
- `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`
- `GET /api/v1/auth/session` (returns `authenticated: false` without cookie)
- `GET /api/v1/auth/public-config` (no secrets)
- `GET /api/v1/auth/oidc/login`, `GET /api/v1/auth/oidc/callback` (fail closed if OIDC is not configured)

**Administrator only**

- `GET /admin/system`, `/admin/health`, `/admin/metrics`, `/admin/audit`
- Admin user/password/role/config mutations

**Session RBAC / API key**

- Domain APIs under `/api/v1/*` require a valid session cookie **or** (when configured) a matching machine API key

## Deferred (not claimed as done)

- Hosted IdP / Azure AD / Okta / Auth0 tenant (customer must issue the OIDC client)
- SCIM / LDAP directory sync
- MFA inside Mercury (use the IdP)
- Kubernetes network policies / service mesh
- Payment / PCI integrations
- Public DNS and publicly trusted TLS certificates (Let's Encrypt overlay exists; certs are not in git)

See [docs/security/EPIC009_RC_NOTES.md](docs/security/EPIC009_RC_NOTES.md) and [docs/pilot/PRODUCTION.md](docs/pilot/PRODUCTION.md).

## Related

- Constitution Article IX  
- Engineering Standards E3–E5  
