# Enterprise Organizations & Multi-Tenancy

Mercury isolates operational data by **organization** and **site**. Sprint 5 persists the full hierarchy in the database and enforces membership-aware access.

## Hierarchy

```
Company
  └── Organization          (public id: organization_id)
        ├── Site            (public id: site_id)
        ├── Department      (optional site binding)
        │     └── Team
        └── Memberships     (user ↔ org role, optional site/dept/team)
```

Seeded demo (idempotent on startup):

| Entity | IDs |
|--------|-----|
| Company | `company-mercury` / `MAG` |
| Organizations | `org-aviation-east`, `org-aviation-west` |
| Sites | `site-cyul`, `site-cyyz` (east); `site-cyvr` (west) |
| Department / Team | Operations East / Watch Floor East |

Built-in operators (`admin`, `operator`, `reviewer`, `viewer`) receive `org_users` + `memberships`. Administrators are members of all seeded orgs; other roles receive the first organization only.

## Isolation rules

1. **Session context** (`GET/POST /api/v1/auth/context`) only lists organizations the caller may access.
2. Switching to an organization without membership returns **403** (audited as a security event).
3. Platform administrators are determined from the **login directory** (`operator_store`), never from membership elevation.
4. Membership roles are limited to **Operator / Reviewer / Viewer** (Administrator assignment rejected).
5. Users without an active membership cannot establish a session (403).
6. Incident, evidence, audit, and decision APIs continue to filter by session `organization_id` + `site_id`.
7. On login and org switch, session `role` is the highest allowed membership role for that organization (capped below platform admin).

## REST APIs

All require an authenticated session. Reads need `org.read`; mutations need `org.manage` (Administrators).

| Method | Path | Notes |
|--------|------|--------|
| GET/POST | `/api/v1/companies` | Create requires admin |
| GET/POST | `/api/v1/organizations` | Filtered by membership |
| GET | `/api/v1/organizations/{id}` | Membership-gated |
| GET | `/api/v1/organizations/{id}/sites` | Membership-gated |
| GET/POST | `/api/v1/sites` | Default org = session org |
| GET/POST | `/api/v1/departments` | Org-scoped |
| GET/POST | `/api/v1/teams` | Org-scoped |
| GET/POST | `/api/v1/org/users` | Admin directory |
| GET/POST | `/api/v1/memberships` | Org-scoped RBAC bindings |
| GET | `/api/v1/org/me` | Current user + memberships |

Mutations emit audit actions such as `org.company.create`, `org.membership.create`.

## Database

- SQLAlchemy models: `backend/app/org/models.py`
- Alembic: `20260812_0002_enterprise_organizations` (after `20260810_0001`)
- SQLite/dev: `ensure_schema()` → `create_all` imports org models
- Postgres: run `alembic upgrade head` before/with deploy

## Auth notes

- Passwords for interactive login remain in the in-memory `operator_store` (hashed).
- Creating `/api/v1/org/users` also registers the user in `operator_store` (default Viewer) so they can log in.
- Org directory passwords are stored hashed on `org_users` for future directory sync; do not treat them as a second live auth source yet.

## Operations

1. Apply migration on Postgres.
2. Restart API (seed runs once when `companies` is empty).
3. Confirm `GET /api/v1/organizations` as admin vs operator.
4. Confirm operator cannot open `org-aviation-west`.

## Out of scope (this sprint)

SSO / Azure AD, MFA, fine-grained permission objects beyond role sets, and frontend redesign remain deferred.
