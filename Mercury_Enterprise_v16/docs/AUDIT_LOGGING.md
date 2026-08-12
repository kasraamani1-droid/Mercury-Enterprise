# Audit Logging

Mercury persists accountability events in `audit_events` with site/org scoping for operator reads and cross-site listing for administrators.

## Recorded actions

| Action | When |
|--------|------|
| `auth.login` | Successful sign-in |
| `auth.logout` | Sign-out |
| `security.login_failure` | Invalid credentials |
| `security.event` | Security-relevant blocks (failed login, rate limit) |
| `user.create` | Admin creates an operator |
| `user.password_change` | Admin rotates an operator password |
| `user.role_change` | Admin changes an operator role |
| `config.change` | Admin updates an allow-listed runtime setting |
| `api.access` | Authenticated mutating API calls when `MERCURY_AUDIT_API_ACCESS=true` (off by default to protect request-path latency) |

Existing domain audits (incidents, approvals, connectors, decisions) continue unchanged.

## APIs

Operator / reviewer (site-scoped):

```http
GET /api/v1/audit
```

Administrator (cross-site):

```http
GET /admin/audit?action=auth.login&limit=100
```

## Retention

`MERCURY_AUDIT_RETENTION_DAYS` (default `365`) filters list queries.

## Security notes

- Passwords are never written to audit `details`.
- Failed logins record the attempted operator name only.
- Admin user/password/role/config mutations always create an audit row.
