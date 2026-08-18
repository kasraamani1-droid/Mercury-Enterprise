# Mercury AEOS — Structure Standard

## Principle

**Additive modular monolith.** Do not rename/move working domain packages in a big-bang. Map logical AEOS layers onto `backend/app/*` and converge via facades.

## Canonical mapping

| Logical AEOS path | Current path | Status |
|-------------------|--------------|--------|
| platform/identity | `platform/` + `security/` | Live |
| platform/organizations | `org/` + `platform` org extensions | Live |
| platform/workflow | `platform/` + `workflow_bridge` | Live |
| platform/audit | `audit.py` + `platform/audit_engine.py` | Live |
| platform/notifications | `platform/` | Live |
| platform/search | `platform/` | Live |
| platform/file_storage | `platform/` file objects | Live (metadata) |
| platform/configuration | `platform/` settings/flags | Live |
| aviation/aircraft | `fleet/` | Live |
| aviation/components | `components/` | Live |
| aviation/maintenance | `maintenance/` + `work_orders/` | Live |
| aviation/planning | `planning/` | Live |
| aviation/technical_library | `publications/` | Live |
| inventory | `logistics/` | Live |
| marketplace | `marketplace/` | Live (readiness) |
| authority | `authority/` | Live (readiness) |
| oem | `oem/` | Live (readiness) |
| shared | `shared/` | Live |
| frontend | `frontend/` | Live (vanilla JS) |
| docs/architecture | `docs/architecture/` | Live |

## Non-goals

- React/Vue/Angular/Next.js frontend rewrite
- Microservices split before shared session store + event bus
- Claiming regulatory approval via Authority domain
