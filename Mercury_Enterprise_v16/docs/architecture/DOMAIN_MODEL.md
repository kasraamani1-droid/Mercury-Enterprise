# Mercury AEOS — Canonical Domain Model

Mercury is an **Aviation Enterprise Operating System**. Domains below are owned packages; every product consumes shared platform services.

## Domain ownership map

| Domain | Ownership (runtime package) | API prefix | Permissions |
|--------|-----------------------------|------------|-------------|
| Platform | `backend/app/platform/` | `/api/v1/platform` | `platform.read\|manage` |
| Identity | platform + `security/` + sessions | `/api/v1/platform/identity`, `/api/v1/auth` | platform + auth |
| Organizations | `backend/app/org/` + platform org extensions | `/api/v1/org`, `/api/v1/platform/org` | `org.*`, `platform.*` |
| Personnel | `backend/app/personnel/` | `/api/v1/personnel` | `personnel.*` |
| Aircraft / Fleet | `backend/app/fleet/` | `/api/v1/fleet` | `fleet.*` |
| Components | `backend/app/components/` | `/api/v1/components` | `component.*` |
| Maintenance | `backend/app/maintenance/` | `/api/v1/maintenance` | `maintenance.*`, `task.*` |
| Planning | `backend/app/planning/` | `/api/v1/planning` | `planning.*` |
| Engineering | planning EO/SB + publications | (via planning/publications) | `engineering.read` |
| Technical Library / Publications | `backend/app/publications/` | `/api/v1/publications`, `/api/v1/library` | `publication.*` |
| Inventory / Supply Chain | `backend/app/logistics/` | `/api/v1/logistics` | `logistics.*` |
| Marketplace | `backend/app/marketplace/` | `/api/v1/marketplace` | `marketplace.*` |
| OEM | `backend/app/oem/` | `/api/v1/oem` | `oem.read` |
| Authority | `backend/app/authority/` | `/api/v1/authority` | `authority.read` |
| Finance | readiness (cost centers on platform) | platform cost centers | platform |
| AI | `backend/app/ai/` + search `ai_metadata_json` | advisory APIs | advisory only |
| Analytics / Executive | reporting + future executive product | `/api/v1/reports` | `reports.read` |

## Shared platform services (mandatory)

| Service | Package | Rule |
|---------|---------|------|
| Identity | platform identity + security operators | No per-product user stores |
| Organization | org + platform facilities/BU/CC | Org isolation on every query |
| Personnel | personnel | Certifications bound to identity |
| Permission | `platform/permission_service.py` + `security/authorization.py` | No module-specific RBAC engines |
| Workflow | `platform` workflow + `workflow_bridge` | Configurable definitions; job cards resolve transitions from engine |
| Notification | platform notifications | Event-driven multi-channel |
| Audit | `platform/audit_engine.py` → `record_audit` | Fail-closed; never bypass |
| Search | platform search + `ai_metadata_json` | AI-ready metadata, no LLM yet |
| File | platform file objects | Versioned metadata + hash + scan status |
| Configuration | platform settings / feature flags | Org + system |
| Event Framework | `platform/event_framework.py` (shims `events/`) | Single bus; future Redis/NATS |
| Integration Framework | `platform/integration_framework.py` | SSO/SCIM/LDAP/OEM/Authority readiness |

## Target vs current structure

Physical folder moves are **deferred** (preserve modular monolith stability). Canonical *logical* layout:

```
backend/app/
  shared/           # ActorContext, pagination
  platform/         # identity, workflow, audit, notify, search, file, config, events, integration
  org/              # organizations
  personnel/
  fleet/            # aircraft
  components/
  maintenance/
  planning/         # engineering orders live here today
  publications/     # technical library
  logistics/        # inventory + supply chain
  marketplace/
  oem/
  authority/
  ai/
```

See [STRUCTURE.md](STRUCTURE.md).
