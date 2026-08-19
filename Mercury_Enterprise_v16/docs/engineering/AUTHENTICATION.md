# Authentication (RC1 Blocker 01)

**Status:** Implemented / verified 2026-08-17  
**Parent:** Mercury Platform RC1 Release Blocker Report (Blocker 01 — Authentication)

## Summary

Operator authentication is a **server-side session** referenced by an opaque `HttpOnly` cookie. Credentials are verified against `org_users` with **Argon2id**, or via **OIDC authorization-code + PKCE** when configured. JWT access/refresh tokens are **not** issued and are **not** accepted as operator sessions.

## API

| Method | Path | Auth | Behavior |
|--------|------|------|----------|
| POST | `/api/v1/auth/login` | Public (rate-limited) | Verify credentials; set session cookie; audit `auth.login`. Disabled when `MERCURY_AUTH_MODE=oidc` unless `MERCURY_ALLOW_PASSWORD_AUTH=true`. |
| POST | `/api/v1/auth/logout` | Public (idempotent) | Delete session + cookie; audit `auth.logout` when a session existed |
| GET | `/api/v1/auth/session` | Public | `authenticated: true/false` (HTTP 200 either way) |
| GET | `/api/v1/auth/public-config` | Public | Auth mode, SSO availability, SIM visibility — no secrets |
| GET | `/api/v1/auth/oidc/login` | Public | 302 to the IdP (PKCE). Fails closed if OIDC is not configured |
| GET | `/api/v1/auth/oidc/callback` | Public | Code exchange, JWKS ID-token verify, userinfo mapping onto `org_users`; set session cookie |
| GET | `/api/v1/auth/context` | Session | Active org/site + switchable tenants |
| POST | `/api/v1/auth/context` | Session | Switch org/site (denied without membership; API-key principals cannot switch) |

There is **no** `/api/v1/auth/refresh` endpoint. Session lifetime is `MERCURY_SESSION_TTL_SECONDS` (cookie `Max-Age` and server `expires_at` stay aligned).

## OIDC / SSO

HTTPS (`HTTPS_ENABLED=true`) requires OIDC at startup. Configure `MERCURY_OIDC_ISSUER`, `MERCURY_OIDC_CLIENT_ID`, `MERCURY_OIDC_CLIENT_SECRET`, and `MERCURY_OIDC_REDIRECT_URI`. The integration is authorization-code + PKCE; identities must already exist in `org_users` unless `MERCURY_OIDC_AUTO_PROVISION=true` (off by default). Session cookies remain opaque — OIDC does not mint Mercury JWTs.

ID tokens are signature-verified from the discovery `jwks_uri` (RS256/ES256 only). Verification covers `iss`, `aud`, `exp`, `nbf`/`iat` (clock skew), `kid`, and `nonce` when nonce was sent. `alg=none`, HMAC, missing kid, and unknown keys are rejected. JWKS fetch failure fails closed (HTTP 503) when OIDC is in use. Userinfo `sub` must match the ID-token `sub`.

PKCE `state` + `code_verifier` (+ nonce) are stored in Redis with a short TTL and consumed once. Production / HTTPS OIDC has **no** in-memory PKCE fallback: Redis down → 503. Local development without `REDIS_URL` may use process memory. The production Compose overlay runs `--workers 2` because sessions and PKCE state are Redis-backed.

Do not insert placeholder IdP credentials. There is still **no** hosted Okta/Auth0/Entra client in this repository; operators must issue a real confidential client.

## JWT and `JWT_SECRET`

| Item | Behavior |
|------|----------|
| Session mechanism | Opaque cookie ID → `session_store` (memory or Redis) |
| JWT access token | **Not issued.** Login JSON has no `token` / `access_token` / `jwt` |
| Refresh token | **Not implemented** |
| `Authorization: Bearer` | Optional **machine API key** when `MERCURY_API_KEY` is set — not JWT validation |
| `JWT_SECRET` | Required in production/HTTPS as a startup secret; also a **legacy SHA-256 pepper** candidate. It does **not** sign session cookies |

## Session management

- Cookie: `HttpOnly`, `SameSite=Lax` (configurable), `Secure` forced in production/HTTPS
- Successful login/OIDC callback invalidates any existing session cookie (session-fixation protection)
- Mutating requests with a foreign `Origin`/`Referer` are rejected (CSRF origin check; SameSite=Lax remains primary)
- Store: in-memory default; Redis when `REDIS_URL` is set. Production OIDC PKCE/state is Redis-only.
- Expired records are rejected on read, not persisted with a synthetic TTL, and swept on the process heartbeat
- Password reset revokes all sessions for that operator (`session_store.delete_for_operator`)

## Middleware and RBAC

- Login bucket is separate from the general `/api` rate-limit bucket (`429` + `Retry-After`)
- `require_session` → cookie session or (optional) API key; else `401 Authentication required`
- `require_permissions` → runtime RBAC (role + temporary access + custom roles) → `403 Insufficient permissions`
- Tenant: login stamps org/site; `assert_org_access` on domain reads/writes. Incident Command and WebSocket isolation: [TENANT_ISOLATION.md](TENANT_ISOLATION.md)

## Audit

| Action | When |
|--------|------|
| `auth.login` | Successful password or OIDC login (`details=method=password|oidc`; no session cookie value) |
| `auth.logout` | Logout with a valid session |
| `security.login_failure` | Invalid credentials |
| `security.login_failure` (`details=rate_limited`) | Login rate-limit 429 |
| `security.authz_denied` | RBAC permission failure |
| `security.event` | Invalid credentials (companion) and denied org context switch |
| `auth.context` | Successful tenant switch |

## Frontend

- Boot: `GET /auth/public-config` (SSO vs password, SIM visibility), then `GET /auth/session`; if unauthenticated, login overlay
- All API fetches use `credentials: "include"`
- `401` on non-login API calls dispatches `mercury:auth-required` and re-opens the overlay
- Sign-out calls `POST /auth/logout` and reloads

## Regression tests

`backend/tests/test_rc1_authentication.py`, `test_cycle6_production_iam.py`, `test_cycle6_idor.py`, `test_cycle7_jwks_pkce.py`, plus existing suites: `test_auth_directory.py`, `test_password_security.py`, `test_epic009_security.py`, `test_hardening_security.py`, `test_production_security.py`, `test_api.py`.
