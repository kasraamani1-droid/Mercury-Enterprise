# Roadmap

Mercury ships as an incremental FastAPI + vanilla JS foundation. Items below are ordered by dependency on that architecture — not a commitment calendar.

## Delivered

| Tag / sprint | Focus |
|--------------|--------|
| V2.0 / package 16.0.0 | Command platform foundation, decisions, hardening |
| **v0.9.1** | Production security & infrastructure (HTTPS, headers, rate limits, Compose production profile) |
| **v0.9.2** | Enterprise observability & operations (logs, metrics, admin APIs, backup scripts) |
| **Sprint 5** | Enterprise organizations & multi-tenancy (companies, sites, departments, teams, memberships) |
| **Sprint 6** | Aircraft registry & fleet management (manufacturers, models, aircraft, registrations, fleets) |
| **Sprint 7** | Aircraft components & configuration (ATA, catalog, serialized parts, install history) |
| **Sprint 7b** | Publications, technical library, personnel, maintenance task engine, certification, signatures, tech logbook, AI stubs |
| **Sprint 8** | Work packages, work orders, job cards, technician/supervisor/QA/ACA execution, dashboards, reports, offline queue |
| **Sprint 8b** | Maintenance operations integration — operator Workspace Engine flow across WO / job cards / logbook / planning / Home |
| **Sprint 8c** | Enterprise logistics operator integration — stores desk, WO/JC material requests, part/PO/tool objects on existing Program B APIs |
| **Sprint 8d** | Maintenance planning operator integration — due/forecast desk, AD/SB/EO, MEL/defects, hangar, selected-check WP generation |
| **Sprint 8e** | Publications / Technical Library + Personnel operator integration — library desk, publication/employee objects, stamp list GET, job-card personnel chips |
| **Sprint 9** | Maintenance programs, MPD, checks, AD/SB/EO, MEL/CDL, deferred defects, forecast/due list, hangar planning, auto WP generation |
| **Program B** | Enterprise logistics — warehouses, part master, stock ledger, rotables, tools, MR/PR/PO, vendors, shipping, material/tool planning bridge |
| **Program A** | Enterprise Platform Foundation — identity, org extensions, RBAC extensions, generic workflow, notifications, files, search, configuration (`/api/v1/platform`) |
| **AEOS Std** | Shared services facades, event/integration frameworks, marketplace/OEM/authority readiness, job-card workflow bridge, architecture docs |
| **Program 11** | Universal Data Fabric — Digital Passports, relationship engine, fabric events, Digital Thread API, governance (`/api/v1/fabric`) |
| **Program 12** | Aviation Digital Ecosystem + Mercury Connect — stakeholder ecosystems, capability maps, enrollments, connector registry |
| **Program 13** | Mercury Digital Marketplace — B2B sellers, catalog, cart, quotes, orders, reviews (`/api/v1/marketplace`) |
| **Program 14** | Mercury Aviation Network — secure collaboration, partnerships, directory, messaging (`/api/v1/network`) |
| **Program 15** | Mercury Digital Twin — asset lifecycle registry, passport binding, configuration, reliability architecture (`/api/v1/twin`) |
| **Program 16** | Mercury Plugin Platform — Garmin, Honeywell, drone, NDT, flight ops, accounting, dashboards, ERP, SMS (safety), weather, fuel (`/api/v1/plugins`) |
| **Program 17** | Mercury Enterprise Event Fabric — versioned catalog, durable store, subscriptions, DLQ, replay (`/api/v1/event-fabric`) |
| **Task 19** | Mercury Enterprise UX 2.0 — design system, app shell, command palette, workspace IA, AEOS portals (no new backend modules) |
| **Task 27** | Mercury Workspace Engine — context-oriented object workspaces (Aircraft, WO, Twin, …) with tabs, rail, AI panel |
| **Task 36** | Mercury AEOS Constitution — master principles, engineering/architecture/product standards, governance |
| **Productization** | Master Implementation Backlog — EPIC-001…012 toward Platform 1.0 RC (`docs/implementation/`) |

## Near term (additive) — post Constitution / backlog

1. **Runtime merge of custom roles / temporary access** into `has_permissions`
2. **Migrate domain status machines** (work orders, logistics approvals) onto the generic workflow engine incrementally
3. **OIDC / SSO adapters** on MFA/SSO-ready identity surfaces — **Cycles 6–8 shipped the OIDC code-flow, JWKS verify, Redis PKCE, production URL validation, and Redis rate limits**; this handoff adds the sequential owner checklist. Remaining work is **owner** IdP credentials, public DNS, issued TLS certs, and a VPS ([docs/pilot/OWNER_HANDOFF.md](docs/pilot/OWNER_HANDOFF.md)). The next *code* cycle waits on those owner actions.
4. **Object store + virus-scan workers** bound to file metadata
5. **Search indexer workers** / future OpenSearch bridge
6. **Runtime persona RBAC** — enforce Technician/Inspector/ACA/Planner/Supervisor overlays
7. **Shared session store** — Redis-backed sessions for multi-worker API
8. **Native hangar scan client** — consume logistics scan APIs
9. **Marketplace payment + shipping Connect adapters** and vanilla JS storefront shell
10. **Cross-tenant public marketplace directory** (opt-in seller visibility)
11. **Federated Aviation Network directory** under active partnerships + E2E messaging adapters
12. **Digital Twin event-driven rebuild** from Fabric + domain auto-link (fleet/components/tools)
13. **Live OEM plugin adapters** (Garmin/Honeywell) and Safety SMS workflows behind Connect bindings
14. **Domain dual-write to Event Fabric** + Redis/NATS Connect adapters

## Deferred platform expansion

Documented as a future multi-service shape (not current runtime):

- Mobile clients  
- Dedicated API gateway service  
- Message bus / event backbone for notifications  
- Full GraphQL facade (REST remains canonical)  
- Kubernetes HA under load  

## Explicit non-goals (current releases)

- Replacing vanilla JS with React/Vue/Angular/Next.js  
- Certified aviation/security operational use without independent validation  
- Per-module duplicate RBAC / audit / workflow / notification engines  
- Equating Digital Twin with a 3D visualization product  
- Embedding live vendor SDKs for OEM plugins without Connect vault bindings  
- Claiming Kafka-class broker semantics for the in-process Event Fabric  

Track implementation truth in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).
