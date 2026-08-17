# Mercury Aviation Enterprise Operating System (AEOS) Constitution

| Field | Value |
|-------|-------|
| **Document** | Mercury AEOS Constitution |
| **Status** | Adopted — Task 36 |
| **Version** | 1.0 |
| **Effective** | 2026-08-14 |
| **Owner** | Mercury Technologies — Founder / CTO / Chief Enterprise Architect |
| **Audience** | All product, engineering, design, security, and partner teams |
| **Authority** | Master policy for Mercury. ADRs, roadmaps, and code must not contradict this Constitution without a formal amendment. |

---

## Preamble

Mercury Technologies builds the **Aviation Enterprise Operating System (AEOS)** — not a point MRO tool, not a single-airport console, and not a disposable demo.

Mercury connects the digital and operational fabric of aviation: operators, airlines, business aviation, OEMs, MROs, suppliers, training organizations, repair stations, authorities, developers, and partners.

This Constitution defines **what Mercury is**, **how Mercury is built**, **how products behave**, and **how decisions are governed**. It is the foundation for all future products.

> **Non-certification notice:** Mercury software is an engineering and enterprise platform. It is not certified operational aviation, airworthiness, or security software. Independent validation and regulatory approval remain external obligations.

---

## Article I — Identity

### 1.1 What Mercury is

Mercury is an **Aviation Enterprise Operating System**.

Mercury is simultaneously:

| Pillar | Meaning |
|--------|---------|
| Enterprise Software | Multi-tenant aviation operations, maintenance, logistics, and governance |
| Developer Platform | APIs, plugins, Connectors, Event Fabric, documentation |
| Marketplace | B2B aviation parts, services, and capability exchange |
| Integration Platform | Mercury Connect — readiness contracts and live adapters |
| Digital Aviation Network | Secure collaboration under partnerships (not social media) |
| AI Platform | Advisory intelligence with humans in control |
| Digital Twin Platform | Lifecycle twins and passports (not a 3D modeler by default) |
| Knowledge Platform | Search, publications, metadata, and future knowledge graph |

### 1.2 What Mercury is not

- Not a standalone “app per feature” that reimplements identity, RBAC, or audit
- Not a React/Vue/Angular rewrite of the operator console (vanilla JS + FastAPI remain canonical unless Constitution is amended)
- Not an autonomous flight or maintenance decision authority
- Not a substitute for OEM manuals, authorities, or certified systems of record without explicit integration and approval

### 1.3 Canonical stack (current epoch)

| Layer | Standard |
|-------|----------|
| Frontend | Vanilla JS, CSS design system, Workspace Engine |
| Backend | FastAPI modular monolith |
| Data | SQLAlchemy + Alembic; PostgreSQL (production), SQLite (local) |
| Edge | NGINX reverse proxy / TLS |
| Contracts | REST `/api/v1`, OpenAPI, session RBAC |

Amendments to stack require ADR + Constitution revision.

---

## Article II — Core Principles

Mercury **is** and **shall remain**:

| # | Principle | Binding interpretation |
|---|-----------|------------------------|
| P1 | **Platform First** | Products consume shared platform services; they do not fork them |
| P2 | **API First** | Every capability is exposed through versioned APIs before UI convenience |
| P3 | **Cloud Native** | Deployable as containers; 12-factor config; health/ready; horizontal readiness |
| P4 | **Event Driven** | Significant state changes publish to Event Framework / Event Fabric |
| P5 | **Digital Twin Native** | Assets of record can bind to permanent twin identity and passport |
| P6 | **Knowledge Graph Ready** | Entities, relationships, and metadata stay graph-compatible |
| P7 | **AI Ready** | Structured metadata and advisory surfaces; no silent autonomous authority |
| P8 | **Security First** | Fail closed; least privilege; secrets outside code; auditability |
| P9 | **Multi-Tenant** | Organization isolation on every query and mutation |
| P10 | **Offline Capable** | Hangar and field flows support queue/sync patterns |
| P11 | **Mobile First for Hangar** | Technician/QA/ACA flows prioritize small-screen, offline-ready UX |
| P12 | **Open Integration** | Connect catalog + adapters; no hard lock-in to a single vendor SDK in core |
| P13 | **Extensible** | Plugins, workflows, feature flags, and object workspaces extend without core forks |
| P14 | **Observable** | Logs, metrics, traces/correlation IDs, health, audit |
| P15 | **Testable** | Independently testable modules; automated tests for contracts and security |
| P16 | **Documented** | Architecture, ADR, API, and operator docs ship with capabilities |

---

## Article III — Engineering Law

Every feature **must**:

1. **Reuse** existing platform services (identity, org, RBAC, workflow, notify, audit, search, files, config, events, integrations).
2. **Avoid duplicate business logic** — no second RBAC engine, second audit store, or second workflow runtime.
3. **Support RBAC** via `has_permissions` / permission service — never UI-only authorization.
4. **Support auditing** for mutating and privileged reads where policy requires.
5. **Support event publishing** for domain-significant state transitions.
6. **Support APIs** with consistent REST, pagination, errors, and OpenAPI models.
7. **Support automation** through workflows, events, and Connect — not only click-paths.
8. **Support documentation** (architecture note or ADR when boundaries change).
9. **Be independently testable** (unit/API/integration as appropriate).

**Forbidden without ADR:** new SPA framework; per-module identity store; bypassing org isolation; AI that executes operational actions without human control.

Full detail: [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md).

---

## Article IV — User Law

Every workflow **must** aim to:

| Outcome | Design obligation |
|---------|-------------------|
| Reduce clicks | Object workspaces, command palette, defaults, bulk actions |
| Reduce training | Consistent patterns, plain language, progressive disclosure |
| Reduce paperwork | Digital signatures, attachments, structured forms replace re-keying |
| Reduce duplicate entry | Single source of truth; cross-domain links; Digital Thread |
| Increase traceability | Audit, timeline, passport/twin history, correlation IDs |
| Increase automation | Forecast → WP, events → notify, workflow transitions |
| Increase safety | Human-in-the-loop; advisory AI; fail closed; clear status |
| Increase productivity | Context tabs, pinned objects, hangar offline queue |

UX is governed by UX 2.0 + Workspace Engine: **work around objects, not menus**.

---

## Article V — Product Law

Every Mercury product **must integrate into** (consume or publish to) the platform fabric:

| Integration | Obligation |
|-------------|------------|
| Digital Twin | Bind or reference twin/passport where an asset lifecycle exists |
| Enterprise Search | Index or emit searchable metadata |
| Notifications | Emit user/org-relevant notifications on key events |
| Workflow Engine | Prefer configurable definitions over hardcoded state machines |
| Marketplace | Expose or consume catalog capabilities when commercial exchange applies |
| AI | Provide advisory metadata; never claim certified autonomy |
| Analytics | Emit measurable events/metrics for executive and ops views |
| Event Fabric | Publish durable domain events for integration and replay |
| Identity | Use platform identity/org/RBAC exclusively |

Products are **modules of AEOS**, not islands.

Full detail: [PRODUCT_STANDARDS.md](PRODUCT_STANDARDS.md).

---

## Article VI — Company Law

Mercury Technologies builds and commercializes:

1. Enterprise Software  
2. Developer Platform  
3. Marketplace  
4. Integration Platform (Connect)  
5. Digital Aviation Network  
6. AI Platform  
7. Digital Twin Platform  
8. Knowledge Platform  

Go-to-market, partnerships, and roadmap prioritization shall reinforce AEOS cohesion over one-off custom projects that fracture the platform.

---

## Article VII — Long-Term Vision

Mercury becomes the operating system connecting:

**Operators · Airlines · Business Aviation · OEMs · MROs · Suppliers · Training Organizations · Repair Stations · Authorities · Developers · Partners**

Success is measured by:

- Shared identity and trust across organizations  
- Continuous Digital Thread from part → aircraft → operation → release  
- Marketplace and network liquidity under compliance constraints  
- Developer ecosystem on Connect, Plugins, and Event Fabric  
- AI that accelerates humans without replacing accountability  

---

## Article VIII — Architecture Sovereignty

### 8.1 Dependency direction

```
Products / Domains
        ↓ consume
Platform Services (Identity, Org, RBAC, Workflow, Audit, Notify, Search, Files, Config, Events, Connect)
        ↓ persist
Data & Event stores
```

Domains **must not** depend on other domains’ internal tables. They integrate via APIs, events, and shared platform primitives.

### 8.2 Additive change

Prefer additive evolution over rewrites. Preserve working modules. Big-bang redesigns require Constitution amendment + ADR series.

### 8.3 Standards documents

| Document | Role |
|----------|------|
| [ARCHITECTURAL_STANDARDS.md](ARCHITECTURAL_STANDARDS.md) | Layering, boundaries, events, data, APIs |
| [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) | Implementation quality bar |
| [PRODUCT_STANDARDS.md](PRODUCT_STANDARDS.md) | Product integration checklist |
| [GOVERNANCE.md](GOVERNANCE.md) | Amendments, ADRs, release gates |

---

## Article IX — Security & Trust

1. Authentication before sensitive operations.  
2. Authorization server-side on every mutating and privileged path.  
3. Tenant isolation is non-negotiable.  
4. Secrets live in environment / vault — never in source defaults for production.  
5. Audit is fail-closed for covered actions.  
6. AI remains advisory unless a future amendment defines supervised automation with explicit controls.  

---

## Article X — Amendments

1. Propose change via ADR (or Constitution amendment RFC).  
2. Impact review: architecture, security, product, UX.  
3. Approval by CTO / Chief Enterprise Architect (and Founder for Articles I–II, VI–VII).  
4. Update Constitution version, CHANGELOG, and affected ADRs.  
5. No silent contradiction in code reviews — cite the Article being waived and the ADR.

---

## Ratification

This Constitution is ratified as **Mercury AEOS Constitution v1.0** under Task 36.

It governs all subsequent programs, products, and engineering decisions unless formally amended.

**Mercury Technologies**  
Aviation Enterprise Operating System
