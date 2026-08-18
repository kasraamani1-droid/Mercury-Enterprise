# ADR-0001 — Mercury is an Aviation Enterprise Operating System, not a point MRO tool

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-08-14 |
| Deciders | Founder and lead architect, principal engineering, product |
| Supersedes | None |
| Superseded by | None |

---

## Context

The aviation maintenance software market is built from point solutions. An operator typically runs a maintenance and engineering system for airworthiness, a separate inventory system for parts, a separate tool-crib system, a separate procurement system, a spreadsheet for hangar and bay planning, a document management system for publications, a separate training and authorization register for personnel, and a general ledger that none of them agree with. Each product is competent at its own scope. Collectively they produce the defining operational failure of the industry: **the maintenance record and the material record do not reconcile, and nobody can prove what happened without a manual investigation.**

The forces pushing toward building another point solution were real and not weak:

| Force toward a point solution | Why it was compelling |
|-------------------------------|----------------------|
| A narrow product ships faster | A job-card execution tool is a quarter of work. An enterprise platform is years |
| A narrow product is easier to sell | The buyer is one department head with one budget and one pain |
| Integration is a recognised market position | "We integrate with your existing systems" is an easier sentence than "replace them" |
| A small team cannot credibly build nine domains | And a platform half-built across nine domains is worse than one domain done well |
| Point solutions can be excellent | Some are. The failure is not in any single product's quality |

Against those forces sat one observation that turned out to decide the question. **The value an operator actually wants is not in any single domain — it is in the joins between them.** Consider the questions that matter most in aviation maintenance, and where they live:

- *Which purchase order bought the part currently installed in this position, and who inspected it on receipt?* Spans procurement, receiving, inventory, configuration.
- *Was the technician who signed this task authorized on that date, and was the tool they used in calibration?* Spans personnel, certification, tooling.
- *Which aircraft in the fleet have parts from this suspect vendor batch?* Spans procurement, inventory, configuration, execution history.
- *What was the configuration of this aircraft on the date of the lease return?* Spans configuration history and utilization over time.
- *Can this work package actually be performed, or will it stop for material?* Spans planning, inventory, and procurement.

Every one of those questions is unanswerable in a landscape of integrated point solutions, not because integration is badly done, but because **an integration moves data between systems while a join requires the data to have been recorded against a shared identity in the first place.** Two systems can exchange a part number all day and still be unable to state which physical unit was installed where, by whom, under what authority, purchased under which order.

There was also a commercial force that made the decision urgent rather than merely correct. A point MRO tool competes with mature incumbents on features, in a market where the incumbents have decades of feature accumulation. A platform that answers cross-domain questions competes on something the incumbents structurally cannot offer, because their architecture is the source of the problem.

Doing nothing was not neutral. Beginning as a point tool would have set the data model, and a data model designed for one domain does not later grow a coherent digital thread — it grows foreign keys to other systems' identifiers, which is precisely the failure being avoided.

---

## Decision

**Mercury is an Aviation Enterprise Operating System. It models the aviation enterprise as one coherent system with one data model, one identity model, one authorization model, and one audit trail — spanning organization, fleet, configuration, publications, personnel, maintenance, execution, planning, and logistics.**

Specifically:

| Commitment | Meaning |
|------------|---------|
| **One data model** | Nine domain modules share one relational schema, one set of identifiers, and one organization dimension. A component, a part master, a task, and a purchase order refer to each other by primary key, not by exchanged business codes |
| **One identity and authorization model** | One session, one permission catalogue, one organization membership model, one certification identity binding. See [ADR-0003](ADR-0003-multi-tenant-org-isolation.md) |
| **One audit trail** | Every mutation across every domain lands in one audit table with one action catalogue. See [ADR-0006](ADR-0006-audit-everywhere-fail-closed.md) |
| **Cross-domain questions are first-class** | The joins listed in Context are queries, not investigations. This is the product |
| **Logistics is in scope from the start** | Not a later module. See [ADR-0007](ADR-0007-logistics-as-integrated-program.md) |
| **Depth over breadth of adjacent markets** | Mercury goes deeper into aviation maintenance rather than sideways into flight operations, crew, revenue, or general ERP |

And the boundaries, which are as much a part of the decision as the scope:

| Mercury is deliberately **not** | Reason |
|--------------------------------|--------|
| A general-purpose ERP | The general ledger, payroll, and corporate finance are solved elsewhere and are not aviation-specific |
| A flight operations, crew, or revenue system | Different domain, different users, different regulatory surface |
| A design or engineering authoring platform | Type design and OEM data authoring belong to the OEM |
| A certified aeronautical product | Mercury holds no certificate, approval, or designation of any kind. See [SECURITY.md §8](../../../SECURITY.md#8-what-mercury-does-not-claim) |
| A safety management system | Mercury is a source of maintenance safety data and an evidence spine. It does not implement the SMS framework |
| A replacement for an operator's procedures, personnel, or accountability | Compliance is a property of an organization. Mercury supports it and cannot confer it |

---

## Consequences

### Positive

- **The cross-domain questions become queries.** Given a part installed on an aircraft, the chain back to the purchase order that bought it is a series of joins rather than an investigation. This is the property everything else in the blueprint is built on, and it is only available because the scope was chosen this way. See [Technical Architecture §6.7](../../02_Architecture/Technical_Architecture.md#67-traceability-chain).
- **The Digital Aircraft Passport becomes possible.** A coherent airworthiness identity for an aircraft requires configuration, life, evidence, publications, and material provenance in one model. It cannot be assembled from integrations. See [ADR-0002](ADR-0002-digital-thread-passport.md).
- **One authorization and audit model instead of nine.** A security review reads one permission catalogue and one audit catalogue. In a point-solution landscape, an operator's real authorization posture is the union of several inconsistent models, which nobody can assess.
- **Planning can be honest about feasibility.** Because planning sees stock, reservations, tooling, and calibration in the same transaction, a work package can be refused rather than optimistically scheduled. A planning tool that cannot see material can only produce plans that are sometimes true.
- **A defensible competitive position.** Mercury competes on coherence, which incumbents cannot retrofit without rebuilding their data models.
- **Consistent conventions across the whole platform.** One module pattern, one error model, one pagination contract, one tenancy rule. See [Coding Standards](../Coding_Standards.md).

### Negative

These are the real costs, and they are accepted rather than minimised.

- **The build is very large.** Nine domains with genuine depth is years of work, and the platform is honest that parts of it are shallower than others. Every "Partial" and "Planned" marker across the blueprint is a consequence of this decision.
- **A large surface is harder to make excellent everywhere.** A dedicated tool-crib product will beat Mercury's tool crib on tool-crib features. Mercury's answer is that the tool crib is bound to the job card, the calibration status blocks the release, and the lost-tool report is in the same audit trail — but on features alone, the point product wins.
- **The sales conversation is harder and longer.** Mercury is bought by an organization rather than a department, which means more stakeholders, longer evaluation, and a higher bar for proof.
- **Implementation is a data migration project.** A coherent model requires coherent data, which means an operator's fragmented history has to be reconciled on the way in — and where it cannot be, [Digital Twin §5.2](../../07_AI/Digital_Twin.md#52-required-properties) requires the gap to be shown rather than smoothed.
- **A single deployable and a single database is a single blast radius.** Mitigated by [ADR-0004](ADR-0004-api-first-modular-monolith.md)'s modularity and extraction seams, but it is a real trade against a service-per-domain topology.
- **Scope pressure is permanent.** Every customer conversation surfaces an adjacent domain — crew, revenue, finance, flight ops — and each request is individually reasonable. The boundary table above exists because saying no repeatedly requires a written position.
- **Cross-module coupling is genuinely present.** Planning calls work orders and logistics; work orders calls maintenance, publications, and personnel. This is acknowledged rather than denied in [Technical Architecture §12.3](../../02_Architecture/Technical_Architecture.md#123-what-it-does-not-buy--stated-plainly).

### Neutral

- The nine modules are `org`, `fleet`, `components`, `publications`, `personnel`, `maintenance`, `work_orders`, `planning`, and `logistics`. Adding a tenth follows the checklist in [Technical Architecture §3.5](../../02_Architecture/Technical_Architecture.md#35-adding-a-module--the-checklist).
- "AEOS" is used consistently in product and documentation as the name of the category Mercury occupies, not as a marketing flourish.
- Adjacent-domain integration remains legitimate and expected — ingesting utilization from a flight data source, exchanging invoices with a finance system. Integration at the boundary is different from being assembled from integrations.
- Edition and packaging decisions are downstream of this scope, not inputs to it. See [Editions](../../05_Product/Editions.md).

---

## Links

**Governs**
[Enterprise Architecture](../../02_Architecture/Enterprise_Architecture.md) · [Domain Architecture](../../02_Architecture/Domain_Architecture.md) · [Technical Architecture](../../02_Architecture/Technical_Architecture.md) · [System Context](../../02_Architecture/System_Context.md) · [Product Family](../../05_Product/Product_Family.md) · [Editions](../../05_Product/Editions.md)

**Explained in depth**
[VISION](../../../VISION.md) · [Company Strategy](../../01_Executive/Company_Strategy.md) · [Mission](../../01_Executive/Mission.md) · [Blueprint README](../../../README.md)

**Business domains this scope serves**
[Airline](../../03_Business/Airline.md) · [MRO](../../03_Business/MRO.md) · [CAMO](../../03_Business/CAMO.md) · [OEM](../../03_Business/OEM.md) · [Leasing](../../03_Business/Leasing.md) · [Authority](../../03_Business/Authority.md)

**Related decisions**
[ADR-0002 — Digital thread and passport](ADR-0002-digital-thread-passport.md) · [ADR-0004 — API-first modular monolith](ADR-0004-api-first-modular-monolith.md) · [ADR-0007 — Logistics as an integrated program](ADR-0007-logistics-as-integrated-program.md)

**Non-claims**
[SECURITY.md §8](../../../SECURITY.md#8-what-mercury-does-not-claim) · [ROADMAP §8](../../../ROADMAP.md#8-explicit-non-goals) · [Regulations documentation set](../../09_Regulations/)

**Register**
[ADR index](README.md)

---

*Mercury Technologies — One Digital Thread. One Digital Aircraft Passport. One Aviation Enterprise Operating System.*
