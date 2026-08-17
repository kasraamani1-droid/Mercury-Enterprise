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
| `approval.request` | Approval request created (durable `approval_requests` row) |
| `approval.approve` | Approval approved (tenant-scoped) |
| `approval.consume` | Approved approval consumed on resolve/close |

Domain audits (incidents, connectors, decisions) continue unchanged. Incident status/event/evidence audits stamp the **resource** organization and site. Operator list remains site-scoped (west rows are not returned to an east reviewer). Approvals themselves are SQL-backed; see [engineering/APPROVAL_PERSISTENCE.md](engineering/APPROVAL_PERSISTENCE.md). Tenant rules: [engineering/TENANT_ISOLATION.md](engineering/TENANT_ISOLATION.md).

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
