# Mercury AEOS — Architectural Standards

**Parent:** [MERCURY_AEOS_CONSTITUTION.md](MERCURY_AEOS_CONSTITUTION.md) Article VIII  
**Version:** 1.0 · 2026-08-14

---

## 1. Architectural style

Mercury runs as an **API-first modular monolith** (ADR: API-first modular monolith / vanilla JS + FastAPI).

| Decision | Standard |
|----------|----------|
| Deployable unit | Single FastAPI app + static frontend (Compose/NGINX) |
| Module boundary | Python package under `backend/app/<domain>/` |
| UI boundary | Vanilla JS modules; no SPA framework in current epoch |
| Future multi-service | Allowed only with ADR; Constitution still applies |

---

## 2. Layering

```
┌─────────────────────────────────────────┐
│  Products / Workspaces (UI)             │
├─────────────────────────────────────────┤
│  Domain APIs (fleet, maintenance, …)    │
├─────────────────────────────────────────┤
│  Platform Services                      │
│  Identity · Org · RBAC · Workflow       │
│  Audit · Notify · Search · Files        │
│  Config · Events · Connect · Plugins    │
├─────────────────────────────────────────┤
│  Persistence · Object metadata · Bus    │
└─────────────────────────────────────────┘
```

**Dependency rule:** Domains may depend on platform and shared. Domains must not import other domains’ internal repositories. Cross-domain orchestration uses APIs, events, or thin application services.

---

## 3. Domain ownership

Canonical map: `docs/architecture/DOMAIN_MODEL.md`.

| Rule | Standard |
|------|----------|
| One owner per concept | No competing tables for the same business entity |
| Logical vs package | Engineering/Analytics may be logical until a package is justified by ADR |
| Soft-delete / history | Consistent within a domain; document cross-domain differences |

---

## 4. Platform services (mandatory reuse)

| Service | Do | Don’t |
|---------|----|-------|
| Identity | Platform + `/api/v1/auth` | Per-product user tables |
| Org / tenancy | `org` + asserts | Trust client-supplied org without check |
| RBAC | Permission service + roles | Hardcoded role strings in many places without matrix |
| Workflow | Definitions + bridge | New state-machine frameworks |
| Audit | `record_audit` / audit engine | Fire-and-forget logs as sole audit |
| Notify | Platform notifications | Ad-hoc email-only forks |
| Search | Platform search index | Per-module search engines |
| Files | Platform file objects | Untracked blob dumps |
| Events | Framework + Fabric per contract | Fourth event bus |
| Connect / Plugins | Catalog + installations | Embed vendor SDKs in core without Connect |

---

## 5. Event architecture

Three layers — keep distinct:

| Layer | Purpose |
|-------|---------|
| Event Framework | In-process pub/sub, request-scoped reactions |
| Digital Thread (`fabric_events`) | Entity/passport timeline |
| Enterprise Event Fabric | Durable catalog, store, subscriptions, DLQ, replay |

Standards:

- Version event types  
- Include org, actor, correlation/trace where available  
- Immutable stores do not soft-delete  
- Replay is explicit and audited  

---

## 6. Digital Twin & Thread

- Twin = permanent UUID lifecycle identity; **not** synonymous with 3D visualization  
- Passport/thread bind assets across domains  
- Reliability/AI twin surfaces are architecture-ready until explicitly productized  

---

## 7. API architecture

| Topic | Standard |
|-------|----------|
| Versioning | `/api/v1` canonical; breaking changes require `/api/v2` + ADR |
| Auth | Session RBAC; machine keys when enforced by security program |
| Errors | Stable `detail`; no stack traces to clients |
| Pagination | Shared helpers; bounded limits |
| Idempotency | Document for create/transition endpoints that need it |
| Gateway | NGINX edge today; dedicated gateway service is deferred, not required for AEOS correctness |

---

## 8. Data architecture

- PostgreSQL for production multi-user  
- Alembic linear migrations  
- Indexes for tenant + common filters (`organization_id`, status, foreign keys)  
- Partitioning plans documented before extreme volume claims  
- Encryption readiness: TLS in transit; at-rest per deployment profile  

---

## 9. Frontend architecture

| Concern | Standard |
|---------|----------|
| Shell | UX 2.0 app shell |
| Objects | Workspace Engine — context tabs + rail |
| Areas | Discovery boards (planning, logistics, …) |
| Design system | Tokens, dark/light, IBM Plex |
| Offline | Queue pattern for hangar (MRO) |

---

## 10. Observability architecture

- Structured logs with request/correlation IDs  
- `/health`, `/ready`, metrics endpoint  
- Audit trail as security observability  
- No silent swallow of authorization failures  

---

## 11. Evolution rules

1. Additive by default.  
2. Shims over big-bang renames.  
3. ADR for boundary moves, new buses, new frameworks.  
4. Constitution amendment for stack epoch changes.  
