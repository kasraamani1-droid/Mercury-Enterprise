# Mercury Aviation Network — Architecture

**Program 14** · Secure professional aviation collaboration platform.

## Positioning

Mercury Aviation Network is **not social media**. It is an enterprise collaboration fabric where:

- Organizations remain **isolated by default**
- Cross-organization work requires an **explicit active partnership**
- Profiles, messaging, document shares, and collaborations are audited
- Authority / certificate fields are readiness metadata — **not** regulatory verification

## Package

`backend/app/network/` — catalog, models, schemas, service, router  
API: `/api/v1/network`  
Permissions: `network.read` / `network.manage`  
Alembic: `20260814_0017`

## Core capabilities

| Area | Behavior |
|------|----------|
| Org profiles | Capabilities, certs, facilities, aircraft/engines, marketplace/careers/training/library refs |
| Professionals | AME→Executive roles with licenses, skills, credentials (opt-in directory) |
| Partnerships | Supplier/customer/partner/… with permissions, contracts, expiry, approve workflow |
| Collaborations | Engineering, repair quotes, tech assist, WP/publication share, document review |
| Document shares | Expiry, watermark, read-only/download/approval-required |
| Messaging | Org↔org, user, project, work package, marketplace scopes |
| Events | Training, conferences, webinars, SB releases, job fairs, maintenance events |
| Directory | Opt-in searchable projection (org-scoped in this release) |

## Security model

1. Tenant isolation via `OrganizationService.assert_org_access`
2. Partnership gate for cross-org collaboration / messaging / document share
3. RBAC on all routes
4. AuditEngine on mutating actions
5. Zero-trust ready metadata (`ai_metadata_json.zero_trust_ready`)

## Related docs

- [NETWORK_ENTITY_RELATIONSHIP.md](NETWORK_ENTITY_RELATIONSHIP.md)
- [NETWORK_WORKFLOW.md](NETWORK_WORKFLOW.md)
- [NETWORK_API.md](NETWORK_API.md)
- [NETWORK_FUTURE_ROADMAP.md](NETWORK_FUTURE_ROADMAP.md)
- [NETWORK_PRODUCTION_READINESS.md](NETWORK_PRODUCTION_READINESS.md)
- ADR-0014
