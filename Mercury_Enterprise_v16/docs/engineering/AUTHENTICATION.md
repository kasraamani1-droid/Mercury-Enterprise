# Authentication (RC1 Blocker 01)

**Status:** Implemented / verified 2026-08-17  
**Parent:** Mercury Platform RC1 Release Blocker Report (Blocker 01 — Authentication)

## Summary

Operator authentication is a **server-side session** referenced by an opaque `HttpOnly` cookie. Credentials are verified against `org_users` with **Argon2id**. Login, logout, session probe, and tenant context are the only auth APIs. JWT access/refresh tokens are **not** issued and are **not** accepted as operator sessions.

## API

| Method | Path | Auth | Behavior |
|--------|------|------|----------|
| POST | `/api/v1/auth/login` | Public (rate-limited) | Verify credentials; set session cookie; audit `auth.login` |
| POST | `/api/v1/auth/logout` | Public (idempotent) | Delete session + cookie; audit `auth.logout` when a session existed |
| GET | `/api/v1/auth/session` | Public | `authenticated: true/false` (HTTP 200 either way) |
| GET | `/api/v1/auth/context` | Session | Active org/site + switchable tenants |
| POST | `/api/v1/auth/context` | Session | Switch org/site (denied without membership; API-key principals cannot switch) |

There is **no** `/api/v1/auth/refresh` endpoint. Session lifetime is `MERCURY_SESSION_TTL_SECONDS` (cookie `Max-Age` and server `expires_at` stay aligned).

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
- Store: in-memory default; Redis when `REDIS_URL` is set
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
| `auth.login` | Successful login |
| `auth.logout` | Logout with a valid session |
| `security.login_failure` | Invalid credentials |
| `security.login_failure` (`details=rate_limited`) | Login rate-limit 429 |
| `security.event` | Invalid credentials (companion) and denied org context switch |
| `auth.context` | Successful tenant switch |

## Frontend

- Boot: `GET /auth/session`; if unauthenticated, login overlay
- All API fetches use `credentials: "include"`
- `401` on non-login API calls dispatches `mercury:auth-required` and re-opens the overlay
- Sign-out calls `POST /auth/logout` and reloads

## Regression tests

`backend/tests/test_rc1_authentication.py` plus existing suites: `test_auth_directory.py`, `test_password_security.py`, `test_epic009_security.py`, `test_hardening_security.py`, `test_production_security.py`, `test_api.py`.
