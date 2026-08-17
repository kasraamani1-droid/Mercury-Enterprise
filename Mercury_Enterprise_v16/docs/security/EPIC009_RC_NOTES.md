# EPIC-009 Security — RC Notes

**Status:** Implemented (2026-08-14)  
**Parent:** [MASTER_IMPLEMENTATION_BACKLOG.md](../implementation/MASTER_IMPLEMENTATION_BACKLOG.md)

## Delivered

| Requirement | Implementation |
|-------------|----------------|
| Redis sessions | `backend/app/security/sessions.py` — memory default; Redis when `REDIS_URL` set; Compose `redis` service |
| Tenant isolation suite | `backend/tests/test_epic009_security.py` — fleet, WO, marketplace, twin, logistics, planning + context switch |
| API key middleware | `backend/app/security/api_key.py` — when `MERCURY_API_KEY` set, accept `X-API-Key` / `Bearer` (constant-time) |
| Cookie Secure | Production/`HTTPS_ENABLED` forces Secure; startup refuses insecure cookies (verified by test) |
| Password hashing (RB-05) | Argon2id via `argon2-cffi`; unique salts; login-time upgrade from legacy SHA-256; production refuses `mercury-dev-pepper` as secret; password reset revokes sessions |
| Authentication (RC1 Blocker 01) | Cookie sessions verified end-to-end; JWT bearer is not an operator session; OpenAPI `SessionCookie`; login 429 audited; frontend 401 re-prompts login |
| Tenant isolation (RC1 Blocker 02) | Incident status/events/evidence org/site scoped; WebSocket incident fan-out tenant-filtered; alerts list/ack/dashboard filtered; guide `docs/engineering/TENANT_ISOLATION.md` |
| XSS sweep | Command palette search/object labels escaped via `esc()` |
| OIDC/SSO | **Deferred** for RC — readiness surfaces only |

## Password hashing (RC1 Blocker 04 / RB-05)

| Aspect | Behavior |
|--------|----------|
| Algorithm | Argon2id (`Type.ID`), PHC encoded string on `org_users.password_hash` |
| Parameters | `MERCURY_ARGON2_TIME_COST` (default 2), `MERCURY_ARGON2_MEMORY_KIB` (default 19456), `MERCURY_ARGON2_PARALLELISM` (default 1) |
| Salts | Unique per hash (`salt_len=16`); never a shared deployment pepper for new hashes |
| Legacy | SHA-256(pepper + NUL + password) hex still verifies, then rehashes to Argon2id |
| Reset | `POST /admin/users/password` writes Argon2id and calls `session_store.delete_for_operator` |
| Tests | `backend/tests/test_password_security.py`, `backend/tests/test_auth_directory.py` |

## Session design

```
REDIS_URL unset     → MemorySessionBackend (single worker / tests)
REDIS_URL set       → RedisSessionBackend (shared across workers)
REDIS_REQUIRED=true → fail startup/ready if Redis unreachable
```

Keys: `mercury:session:{id}` with TTL aligned to `MERCURY_SESSION_TTL_SECONDS`.  
Context switches (`POST /api/v1/auth/context`) re-save the session record (required for Redis).  
Password changes revoke all sessions for that operator.

## Machine API key

- Empty `MERCURY_API_KEY` → session cookies only (browser default).  
- Set key → alternative auth for automation; org/site/role from `MERCURY_API_KEY_ORG_ID` / `SITE_ID` / `ROLE`.  
- Machine principal (`api-key`) has **synthetic single-org membership** (not platform admin).  
- API-key sessions **cannot** switch org context.

## Deferred (explicit RC exclusion)

- OIDC / Azure AD / SSO / MFA  
- SCIM / LDAP provisioning  
- Full PKI / hardware tokens  
- Kubernetes network policies  

## Production readiness (EPIC-009)

**CONDITIONAL GO** for security baseline on pilot Compose with Redis + Secure cookies + Argon2id + tenant tests green.  
Full Platform RC still depends on remaining identity durability (RB-04) and explicit non-goals. Incident IDOR (RB-01) and WebSocket tenant leak (RB-02) closed 2026-08-17.
