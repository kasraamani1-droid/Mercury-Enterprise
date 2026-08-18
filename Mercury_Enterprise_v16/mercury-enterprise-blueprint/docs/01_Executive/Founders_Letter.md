# Executive — Founders' Letter

| Field | Value |
|-------|-------|
| Document | Founders' Letter |
| Product | Mercury Aviation Enterprise Operating System (AEOS) |
| Organization | Mercury Technologies |
| Audience | Customers, employees, partners, investors, aviation authorities |
| Status | Founding document — amended only by the founders, with a [../../CHANGELOG.md](../../CHANGELOG.md) entry |
| Related | [Vision.md](Vision.md) · [Mission.md](Mission.md) · [Company_Strategy.md](Company_Strategy.md) |

---

## 1. Purpose of this letter

This letter records **why Mercury Technologies was founded, what we observed that convinced us it was necessary, and what we commit to as the company grows**. It is deliberately placed inside the engineering blueprint rather than in a marketing folder, because the commitments in it are meant to constrain technical decisions — not to decorate them.

If a future decision at Mercury conflicts with this letter, the letter is the reference point for challenging that decision.

---

## 2. To our customers, colleagues, and partners

Aviation is the most rigorously evidenced industry in the world, and it runs on records that do not talk to each other.

We did not start Mercury because we thought aviation lacked software. Aviation has an enormous amount of software. We started Mercury because of a pattern we kept encountering, in different countries, at different scales, in operators and maintenance organizations that were run by serious, competent professionals:

**The people who knew the aircraft best spent an extraordinary share of their time proving things that the organization already knew.**

A planner would know a check was coming and still spend a morning assembling what it required, because the maintenance programme lived in one place, the aircraft's accumulated life in another, and the material availability in a third. A continuing airworthiness engineer would know an Airworthiness Directive had been complied with and still rebuild the evidence for it, because the compliance record was a spreadsheet cell pointing at a scanned document. A technician would finish a task correctly and then re-enter the same information into two systems and a paper card. A lessor's technical representative would arrive for a redelivery and spend weeks reconstructing a story that had actually happened, correctly, over eight years — but had never been recorded as one connected narrative.

None of this was anyone's fault. It was the accumulated result of solving each problem well, separately, over three decades. But the cost was real: aircraft on ground, repeat findings, expedited freight, disputed redeliveries, and — the part that mattered most to us — safety-critical judgement being made by people whose attention was partly consumed by reconciliation work.

We concluded that the industry's problem was no longer any individual function. **It was the space between the functions.** And you cannot fix the space between functions by adding another function.

---

## 3. What we decided to build

We decided to build an operating system.

Not a maintenance, repair and overhaul (MRO) product with integrations. Not a continuing airworthiness management organization (CAMO) tool with an export. An **Aviation Enterprise Operating System** — a common substrate providing organizations and isolation, master data, permissions, audit, events, and contracts, on which every aviation function can run without re-inventing those primitives and without creating another island.

Two ideas define it, and we chose them before we wrote the first line of code:

**One Digital Thread.** Every record links, durably and navigably, to the records it concerns. A job card links to the task, the task to the immutable publication revision that authorized it, the certification to the person and their qualifications, the removed component to its life counters, the installed part to its receiving inspection and its vendor. Not copies. Links. Follow any of them, in either direction, and the narrative holds.

**One Digital Aircraft Passport.** Each aircraft has exactly one logical record of identity, configuration, accumulated life, open items, programme status, and airworthiness evidence — computed from immutable events, continuously true, and presentable as evidence rather than as a summary that then needs proving.

These are not features. They are the reason the company exists. Every capability we build is judged by whether it strengthens them.

---

## 4. What we chose to be uncomfortably strict about

Founding a company involves choosing where to be flexible and where to be rigid. We were deliberate about the rigid parts, because in a system of airworthiness record, flexibility in the wrong place is how false records get made.

**Audit is fail-closed.** If we cannot write the audit record for completion of work, an inspection, or a release, the action does not succeed. We accept that this occasionally refuses an action a user wanted. An unaudited release is worse than a refused one. We would rather explain a refusal than explain a record we cannot account for.

**Evidence is immutable.** Publication revisions, digital signatures, installation history and technical logbook entries cannot be edited. Corrections are appended and preserve what came before. Released work cannot be mutated, and a second release is refused. History is not a mutable field.

**The person who performs work cannot inspect it.** This is enforced in the platform, not requested by procedure. If an organization's process depends on the same person doing both, our software will decline — and we think that is the correct behaviour for software that produces airworthiness evidence.

**Nothing is simulated.** Where we do not yet have real cryptographic signature providers, we refuse signature methods that would need to be faked rather than shipping something that looks like a signature and is not one. There are no mock endpoints, no placeholder logic, and no demonstration paths that behave differently from production behaviour.

**Isolation is never a filter added later.** The organization is the isolation boundary, and every entity is organization-owned from the moment it is introduced. We are candid, in [../../SECURITY.md](../../SECURITY.md), about where uniform enforcement is still being extended across engines rather than implying the work is finished everywhere.

**We claim only what exists.** There is no compliance badge in this repository or in our product that we have not independently earned — no SOC 2 report, no ISO/IEC 27001 certificate, no authority approval of the software. Section 8 of [../../SECURITY.md](../../SECURITY.md) lists what we do not claim, in detail, on purpose. We would rather lose a deal to a competitor with a more confident slide than win one on a claim we cannot substantiate to an auditor.

---

## 5. What we chose not to do

**We will not rewrite the platform for fashion.** Mercury's runtime is a vanilla JavaScript frontend and a FastAPI backend with repository, service and thin-router layering, PostgreSQL, and Alembic-managed migrations. It works, it is inspectable, it has no framework churn tax, and it lets a new engineer read a whole request path in an afternoon. We are not migrating to a single-page-application framework. The engineering budget of this company goes into aviation capability, not into re-implementing a working user interface in a newer idiom.

**We will not replace working code because we would have written it differently.** Changes are additive. Institutional knowledge is embedded in code that has survived real use, and we treat that as an asset rather than as debt.

**We will not let artificial intelligence release an aircraft.** We are building Mercury to be AI-ready — structured, indexed, cross-referenced data — and we expect prediction and assistance to become genuinely valuable. But approval, certification and release authority belong to qualified people and approved organizations under regulation. AI at Mercury advises. Humans decide, sign, and answer for it. We are not going to be the company that blurred that line.

**We will not pretend to be an authority.** Mercury produces evidence and computes status. It does not confer compliance, and using our software does not make an organization compliant. Compliance is a property of an organization's exposition, procedures and people.

**We will not treat military aviation as a marketing line.** It is a documented future domain. We are designing for segregation, classification handling and disconnected deployment so that it is achievable without re-architecting. We claim no current accreditation, and we will not imply one.

---

## 6. What we are building on today

We think a founding letter should be checkable, so here is the honest state of things.

The runtime platform today carries organizations and multi-tenancy with membership-aware session context; the aircraft registry and fleets; ATA chapters, component catalog, serialized components, immutable installation history and Time Since New, Time Since Overhaul, Cycles Since New and Cycles Since Overhaul tracking; the technical library with typed publications, revision history and applicability; personnel, qualifications and airworthiness certification authority (ACA) authorizations; the maintenance task engine and technical logbook with append-only amendment; work packages, work orders and job cards with validated transitions, double inspection, quality assurance queues, ACA release and immutable signatures; maintenance planning with programmes, maintenance planning document tasks, checks, Airworthiness Directives, Service Bulletins, Engineering Orders, Minimum Equipment List and Configuration Deviation List items, deferred defects, utilization counters, a forecast engine and automatic work-package generation; and Program B enterprise logistics with warehouses, part master, stock ledger, rotables, tool crib and calibration, the full procurement chain, vendors, shipping and scan interfaces — with material and tool demand derived from the same forecast that drives the hangar, rather than from a separate model that would inevitably diverge.

What is not built yet is written down as not built: federated enterprise identity, cryptographic signature providers, cross-organization ecosystem exchange at scale, the knowledge graph and predictive capability, and the military domain. They are sequenced in [../../ROADMAP.md](../../ROADMAP.md), with the near-term assurance work listed first because assurance is what earns the right to the rest.

---

## 7. Our commitments

**To our customers.** Your data is isolated, your record is provable, and you will be told what is delivered and what is planned before you buy. Your workflow will not be broken by a change we made for our own convenience. When we find a problem in our software, we will tell you.

**To our colleagues.** You will work on a stable architecture rather than a moving one. You will be expected to read before you write, to reuse before you add, to record decisions as Architecture Decision Records, and to stop and ask when something is unclear rather than guess. Raising a concern — about safety, security, data integrity, or an overstated claim — will always be treated as doing your job well. Concealing a mistake will not.

**To our partners.** Integration is a first-class, documented path, not a favour. Your data carries its provenance into the thread, and your access is scoped and audited like everyone else's.

**To aviation authorities.** We will make oversight easier by making records complete, immutable where it matters, and fully audited. We will never represent our software as approved, certified or accepted by you, and we will correct anyone at Mercury who does.

**To ourselves.** We will keep this blueprint as the single source of truth. Where the runtime and the blueprint diverge, we will raise a decision record and fix the blueprint rather than let two versions of the truth exist. And we will keep the uncomfortable sections — the non-claims, the known gaps — in the documents customers actually read.

---

## 8. The standard we hold ourselves to

There is a specific moment we designed this company around.

It is three in the morning in a hangar. A check is overrunning. A technician has found something that was not in the package. A supervisor needs to know whether the part on the shelf is the right one, whether it has provenance, whether the person available to sign is authorized to sign this, and whether the aircraft can be released for the first departure.

Everything Mercury builds is judged by whether it makes that moment better: whether the answer is on the screen, whether it is true, whether it is provable afterwards, and whether the person who acted on it is protected by a record that shows exactly what they knew and what they did.

If a feature does not help that moment, it is not a priority. If a feature makes that moment faster but the record weaker, it does not ship.

---

## 9. Closing

Aviation earned its safety record through discipline about evidence. Our contribution is not to add discipline — the industry has plenty — but to remove the reconciliation tax that discipline currently costs, so that the professionals carrying the responsibility can spend their attention on the aircraft rather than on assembling proof of what they already know.

That is what One Digital Thread means. That is what One Digital Aircraft Passport means. That is the whole company.

**The Founders**
Mercury Technologies

---

## 10. Related documents

| Topic | Document |
|-------|----------|
| Root vision statement of record | [../../VISION.md](../../VISION.md) |
| Extended executive vision | [Vision.md](Vision.md) |
| Mission and operating commitments | [Mission.md](Mission.md) |
| Company strategy | [Company_Strategy.md](Company_Strategy.md) |
| Security posture and explicit non-claims | [../../SECURITY.md](../../SECURITY.md) |
| Delivery sequencing and non-goals | [../../ROADMAP.md](../../ROADMAP.md) |
| Conduct and integrity obligations | [../../CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md) |
| Enterprise architecture | [../02_Architecture/Enterprise_Architecture.md](../02_Architecture/Enterprise_Architecture.md) |
| Digital Thread specification | [../04_Data/Digital_Thread.md](../04_Data/Digital_Thread.md) |

---

*Mercury Technologies — One Digital Thread. One Digital Aircraft Passport. One Aviation Enterprise Operating System.*
