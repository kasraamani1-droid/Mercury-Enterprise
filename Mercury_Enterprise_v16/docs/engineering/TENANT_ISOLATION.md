# Tenant Isolation (RC1 Blocker 02)

**Status:** Implemented / verified 2026-08-17  
**Parent:** Mercury Platform RC1 Release Blocker Report (Blocker 02 — Tenant Isolation)

## Summary

Organization is the tenant boundary; site is the operational scope inside an organization. Domain APIs resolve `organization_id` from the session (optional request override is membership-checked). Command incident writes and WebSocket incident fan-out use the same org/site stamp. JWT is not a tenant mechanism.

## Enforcement points

| Layer | Mechanism |
|-------|-----------|
| Session | Login stamps `organization_id` / `site_id`; `POST /api/v1/auth/context` requires membership (`assert_org_access`) |
| HTTP | `require_session` then `require_permissions` (role + org-scoped temp/custom grants) |
| Domain SQL | `resolve_org` / `assert_org_access` plus `organization_id` predicates on list/get |
| Incidents | List uses org+site filter; get/status/events/evidence/assessment/report use `_get_scoped_incident` (404 on miss or cross-tenant) |
| Approvals | Durable `approval_requests` org/site scoped (RC1 Blocker 03) |
| Audit | `record_audit` always stores org/site; operator `GET /api/v1/audit` is site-scoped; `/admin/audit` is administrator cross-site |
| Alerts | In-memory `AlertManager` filters list/ack/dashboard by session org/site; platform alerts with no org remain visible |
| WebSocket | Connect stamps org/site from the cookie session. Incident/timeline broadcasts pass those ids. Heartbeats omit filters (no tenant payload) |

## APIs that were RC1 defects (now closed)

| Method | Path | Isolation |
|--------|------|-----------|
| PATCH | `/api/v1/incidents/{id}/status` | `_get_scoped_incident`; audit uses resource org/site |
| POST | `/api/v1/incidents/{id}/events` | Same; WebSocket `timeline.event` is tenant-filtered |
| POST | `/api/v1/incidents/{id}/evidence` | Same; evidence row stamped from the incident tenant |
| GET/POST | `/api/v1/alerts`, `/api/v1/alerts/{id}/ack` | Session org/site filter |
| WS | `/api/v1/ws` | Authenticated; incident events only to matching subscribers |

Cross-tenant UUID access returns **404** (does not disclose that the resource exists in another tenant).

## RBAC

Permissions are evaluated for the **active session organization** (`runtime_authz.require_allowed`). Membership still gates which org a principal may switch into. A Viewer in east cannot mutate east incidents (`403`); an Operator in east cannot mutate west incidents (`404`).

## Residual (not Blocker 02)

- Alerts and Command decision/mission stores remain in-process (durability is a separate major).
- `/admin/audit` is intentionally cross-site for administrators.
- Machine API keys cannot switch org context (EPIC-009).

## Regression tests

`backend/tests/test_rc1_tenant_isolation.py` plus existing suites: `test_epic009_security.py`, `test_approval_persistence.py`, `test_audit.py`, domain `test_*_tenant_isolation*` modules.
