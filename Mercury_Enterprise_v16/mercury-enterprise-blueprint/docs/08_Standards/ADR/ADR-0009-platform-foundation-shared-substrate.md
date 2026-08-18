# ADR-0009 — Platform Foundation as shared AEOS substrate

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-08-14 |
| Deciders | Lead Architect / Program A |
| Tags | platform, identity, rbac, workflow, notifications, audit, files, search, configuration |

## Context

Mercury is becoming an Aviation Enterprise Operating System with many products (MRO, CAMO, Airline, OEM, Marketplace, Authority, Careers, Academy, AI, Mobile, Executive, Connect, Digital Twin). Point solutions that each invent their own RBAC, workflow, audit, notifications, and file handling create divergence, compliance risk, and duplicated logic.

## Decision

Ship a single reusable **Platform Foundation** package (`backend/app/platform/`) that every Mercury product must share for:

1. Identity extensions (API keys, PATs, MFA enrollment; SSO surface later)
2. Organization extensions (business units, cost centers, facilities)
3. RBAC extensions (templates, custom roles, temporary access, permission audit) on top of central `has_permissions`
4. Generic workflow engine (data-driven states/transitions — no domain hardcoding)
5. Notification platform (multi-channel, event-driven queue)
6. Audit via existing fail-closed `record_audit` (never a second bypassable path)
7. File metadata platform (versioning, hash, virus-scan interface)
8. Search document index
9. Configuration (settings, feature flags, regional/license keys)
10. REST API surface under `/api/v1/platform`

Domain modules remain responsible for domain entities; they consume platform services rather than re-implementing them.

## Consequences

### Positive

- One place to harden identity, audit, workflow, and notifications
- Workflow designer UI can edit JSON definitions without engine rewrites
- Products stay additive on the modular monolith

### Negative / accepted debt

- Existing domain status machines (work orders, logistics) are not fully migrated onto the generic engine in Program A — migration is incremental
- MFA/SSO are enrollment/ready surfaces; IdP integration remains near-term
- Blob bytes stay behind `storage_uri`; object store binding is deferred
- Temporary access / custom roles are persisted and audited; full runtime merge into `has_permissions` is near-term

## Alternatives considered

- Per-product RBAC/workflow packages — rejected (duplication, inconsistent audit)
- External BPM/IdP-only — rejected for foundation phase; keep in-process engine with future bus/hooks
- Rewrite domain modules onto engine immediately — rejected (breaks compatibility)

## Related

- [docs/PLATFORM_OVERVIEW.md](../../../docs/PLATFORM_OVERVIEW.md)
- ADR-0004 API-first modular monolith
- ADR-0006 Audit everywhere fail-closed
