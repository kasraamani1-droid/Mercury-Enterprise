# ADR-0005 — Vanilla JavaScript frontend and FastAPI / PostgreSQL backend

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-08-14 |
| Deciders | Lead architect, security lead, product leadership |
| Affects | [Technical Architecture](../../02_Architecture/Technical_Architecture.md) · [UI Standards](../UI_Standards.md) · [API Standards](../API_Standards.md) · [Coding Standards](../Coding_Standards.md) · [README.md](../../../README.md) · [ROADMAP.md](../../../ROADMAP.md) |
| Canonical slug | `ADR-0005-vanilla-js-fastapi-stack.md` |
| Legacy slug | `ADR-0001-vanilla-js-fastapi-aeos.md` (same decision; renumbered to avoid colliding with ADR-0001 AEOS scope) |
| Supersedes | — |
| Superseded by | — |

---

## Context

Mercury's Aviation Enterprise Operating System (AEOS) is built as a **FastAPI application serving a vanilla JavaScript, HTML, and CSS frontend with no build step**. The frontend is native ES modules loaded directly by the browser; there is no bundler, no transpiler, no `package.json` in the deployment path, and no single-page-application framework.

This shape was not chosen by default. It is questioned regularly — by contributors arriving from framework-centric backgrounds, by prospective partners who equate a framework with modernity, and by the reasonable observation that most enterprise interfaces of Mercury's ambition are built with React or Angular. The decision therefore needs to be recorded with its reasoning rather than defended repeatedly in review.

The forces that shaped it:

1. **The interface is an operational tool, not a consumer product.** Mercury's users are technicians, inspectors, stores keepers, planners, and ACA holders working from tablets and shared shop-floor terminals. They need contrast, target size, keyboard operability, and unambiguous status — none of which a framework provides and all of which a framework's abstractions can obscure.

2. **The frontend's job is genuinely modest.** Render server-authoritative data, submit forms, switch workspaces, and receive notifications. There is no client-side collaboration, no optimistic local editing, no offline reconciliation, and no client-owned domain model. The problems SPA frameworks solve well are largely problems Mercury does not have — and one of them, optimistic local state, is a problem Mercury deliberately refuses to have, because a maintenance record shown from stale local state is a safety issue.

3. **Supply chain surface is a regulatory concern, not only an engineering one.** A frontend with zero dependencies has no transitive dependency tree, no lockfile drift, no install step in the deployment path, and no framework upgrade treadmill. For a platform whose evidence chain is inspected by aviation authorities, "the deployed frontend is the authored frontend" is a genuine assurance property: what a reviewer reads is what a technician runs.

4. **Longevity requirements exceed framework lifespans.** Aircraft records are retained for the life of the asset plus an authority-required period — decades. A frontend framework's major-version cadence measured against that horizon implies repeated, non-optional rewrites of an interface that regulators, customers, and operators have learned.

5. **FastAPI is the right backend for the opposite reasons.** It provides exactly what Mercury needs and little that it does not: Pydantic validation at the boundary, dependency injection that makes permission gates declarative, and **OpenAPI generated from the code**, so the published contract cannot drift from behaviour. Combined with SQLAlchemy 2.0 and Alembic, it gives a typed, transactional, migration-disciplined backend without a framework opinion about how the domain should be modelled.

6. **The constraint has been tested by delivery, not asserted.** Twelve workspaces — including the enterprise logistics program, maintenance planning, work order execution, and the certification chain — are built and working under it. The absence of a framework has not blocked a capability.

---

## Decision

**Retain vanilla JavaScript, HTML, and CSS with native ES modules and no build step for the Mercury operator interface, and FastAPI with SQLAlchemy 2.0, Pydantic 2, and Alembic for the backend. Do not introduce React, Vue, Angular, Svelte, Next.js, or any other single-page-application framework, bundler, or transpiler into the operator interface.**

Specifically:

| Layer | Decision |
|-------|----------|
| Frontend language | ES modules, native, loaded directly by the browser |
| Frontend build | **None.** No bundler, transpiler, minifier, or compile step in the deployment path |
| Frontend dependencies | **None.** No `package.json` for the operator interface; no framework, no utility library, no CSS framework |
| Frontend structure | One module per workspace, exporting `refresh<Name>Workspace()` and `initialize<Name>()`; all network access through `api.js` — see [UI Standards](../UI_Standards.md) |
| Backend framework | FastAPI, synchronous endpoints over a synchronous SQLAlchemy session |
| Contracts | Pydantic 2 request and response models; OpenAPI generated, never hand-maintained |
| Persistence | SQLAlchemy 2.0 declarative typing; PostgreSQL in production |
| Schema evolution | Alembic, forward-only and additive |

Third-party frontend assets, where genuinely unavoidable, are **vendored and pinned locally** rather than linked from a content delivery network, because the deployed content security policy is `script-src 'self'`.

This decision is reversible only by a superseding ADR that demonstrates a capability Mercury requires and cannot deliver under the constraint. "Developer familiarity", "hiring", "modernity", and "the ecosystem" are explicitly not sufficient grounds, because each is a cost that a framework also imposes in its own direction.

---

## Consequences

### Positive

| Consequence | Detail |
|-------------|--------|
| **Zero frontend supply-chain surface** | No transitive dependencies to audit, patch, or explain to a security reviewer |
| **The deployed artefact is the authored artefact** | No source-map indirection between review and runtime — an assurance property for an audited platform |
| **No upgrade treadmill** | Browser platform features are backwards compatible in a way framework major versions are not |
| **Fast initial load by construction** | No framework runtime, no hydration, no bundle to parse |
| **Low onboarding cost for the interface** | A developer reads one file and understands one screen; there is no framework mental model to acquire first |
| **The API is genuinely the product** | With no framework-coupled client, integrators are peers of the built-in interface rather than second-class consumers. See [API Standards §2](../API_Standards.md#2-design-principles) |
| **Backend contract cannot drift** | FastAPI generates OpenAPI from the same models that validate requests |
| **Declarative authorization** | Dependency injection makes the permission gate visible in every route signature |
| **Aviation-appropriate longevity** | The interface can plausibly outlive several framework generations |

### Negative

| Consequence | Mitigation |
|-------------|-----------|
| **No component model, so markup is repeated across screens** | A disciplined shared CSS component vocabulary and small render helpers. Accepted cost; it is visible repetition rather than hidden abstraction |
| **No reactive binding — the developer must re-render explicitly** | The established `refresh<Name>Workspace()` pattern. This also enforces the correct behaviour: re-read from the server rather than patch local state |
| **Rendering with template literals makes escaping a manual obligation** | A mandatory `esc` helper, and a review rule with no exceptions. This is the sharpest edge of the decision, and [UI Standards §6.1](../UI_Standards.md#61-escaping-is-mandatory) records the surfaces where it has already been missed |
| **`index.html` holds every workspace's markup and grows** | Splitting into server-included fragments is a named enhancement that must not introduce a build step |
| **No framework testing ecosystem for the frontend** | Backend tests exercise the full HTTP contract; frontend verification is manual against a documented checklist. A genuine gap, honestly recorded |
| **Some candidates will find the choice unattractive** | Stated openly in recruitment. The reasoning above is the answer, and it is a reasonable one |
| **No client-side router, so no deep linking today** | A hash-fragment implementation of roughly fifteen lines, listed in [UI Standards §14](../UI_Standards.md#14-future-enhancements) |

### Operational

- Deployment of the frontend is a static file copy behind NGINX; there is no build stage to fail and no build cache to invalidate.
- The content security policy can be strict (`script-src 'self'`) precisely because there is no framework requiring inline execution or `eval`.
- Backend upgrades are ordinary Python dependency upgrades with an upper major bound; the frontend is unaffected by them entirely.
- A frontend defect is diagnosed by reading the shipped file in the browser's debugger, with no source map and no compiled intermediate.

---

## Alternatives considered

### 1. React (with or without Next.js)

**Rejected.** It is the default choice for interfaces of this ambition, and the reasons against it are specific rather than reflexive: a build pipeline and dependency tree in the deployment path; a component and hooks model that most Mercury screens do not need; client-side state management that invites exactly the optimistic local state Mercury refuses; and a major-version cadence that implies periodic non-optional migration of an interface with decades-long relevance. Next.js additionally introduces server-side rendering and routing conventions that duplicate responsibilities FastAPI and NGINX already discharge.

### 2. Vue or Svelte

**Rejected.** Both are lighter than React and Svelte in particular compiles away much of its runtime. Neither changes the fundamental objections: a build step, a dependency tree, and a framework lifecycle. Svelte's compile requirement is a direct contradiction of "the deployed artefact is the authored artefact", which is the property Mercury values most.

### 3. Angular

**Rejected.** The heaviest option, with the strongest opinions about application structure. Its dependency injection and module system would duplicate structure Mercury already has in its backend, and its upgrade history is the least compatible with a decades-long horizon.

### 4. Web Components with a lightweight helper library

**Considered seriously, rejected.** This is the most credible alternative: it would give a genuine component model using platform standards, with a much smaller dependency than a framework. It was rejected because a helper library is a framework that has not yet grown, because the shadow DOM complicates the global CSS component vocabulary Mercury already relies on, and because the marginal benefit over disciplined render functions did not justify introducing the first frontend dependency. **This is the alternative most likely to be revisited**, and if it is, it will be through a superseding ADR that addresses styling, accessibility, and the no-build-step constraint explicitly.

### 5. Server-side rendering with a Python template engine

**Rejected.** It would eliminate frontend JavaScript almost entirely and is genuinely attractive for form-heavy screens. It was rejected because it couples the interface to the backend's rendering, which contradicts the API-first principle: Mercury wants integrators to consume the same contract the interface does. It would also make the real-time notification path and the incremental workspace refresh substantially more awkward.

### 6. Keep vanilla JavaScript but add a build step for bundling and minification

**Rejected.** This is the smallest possible concession and it was refused deliberately, because it surrenders the property that makes the rest of the decision coherent. Once a build step exists, adding a transpiler is a configuration change, and adding a framework is then a dependency away. The performance benefit is negligible for an application whose bundle would be a few hundred kilobytes of unminified, HTTP/2-multiplexed, gzip-compressed modules.

### 7. A different backend framework — Django, Flask, or Node.js

**Rejected.** Django brings an ORM, admin, and template layer that would conflict with the repository, service, and router pattern in [ADR-0004](ADR-0004-repository-service-router.md). Flask would require assembling validation, dependency injection, and OpenAPI generation by hand — the exact things FastAPI provides coherently. Node.js would unify the language across tiers, which is a real benefit, at the cost of Python's data, scientific, and forthcoming AI ecosystem, which [AI Strategy](../../07_AI/AI_Strategy.md) depends on.

---

## Compliance and security impact

| Concern | Impact |
|---------|--------|
| **Isolation** | None directly. Tenancy is enforced server-side and is unaffected by the client technology. The absence of a client-side framework reinforces that no isolation decision can accidentally migrate into the client |
| **RBAC** | Positive. FastAPI dependency injection makes the permission gate a visible part of every route signature, which is materially easier to audit than middleware-based or decorator-scattered authorization |
| **Audit** | Neutral to positive. All auditable acts occur server-side; the client cannot suppress an audit record because it never writes one |
| **Signatures** | Positive. Signing credentials are collected by a plain form and posted directly, with no framework state layer that could retain a credential in memory or in a serialised store |
| **Supply chain** | **Strongly positive.** A frontend with no dependencies cannot be compromised through a dependency. This is the single largest security benefit of the decision, and it is a real one: framework supply-chain compromises have occurred and will occur again |
| **Content Security Policy** | **Strongly positive.** `script-src 'self'` with no `unsafe-eval` and no `unsafe-inline` for scripts is achievable because nothing requires them. The one current violation — a mapping library linked from a public content delivery network without subresource integrity — is recorded as debt in [UI Standards §12](../UI_Standards.md#12-security-considerations) and is remediated by vendoring |
| **Cross-site scripting** | **The principal risk this decision creates.** Template-literal rendering makes escaping a manual obligation, and known unescaped surfaces exist. The mitigation is a mandatory helper plus a review rule; the honest position is that a framework's automatic escaping would remove this class of defect, and Mercury accepts the risk in exchange for the properties above — with the obligation to eliminate the remaining unescaped surfaces |
| **Regulatory evidence** | Positive. "The deployed interface is the reviewed interface" simplifies any assurance argument about what an operator actually saw when they signed |
| **Accessibility** | Neutral. The framework choice neither helps nor hinders; requirements and the honest current position are in [UI Standards §10](../UI_Standards.md#10-accessibility) |

---

## Related documents

**Standards**
[UI Standards](../UI_Standards.md) · [API Standards](../API_Standards.md) · [Coding Standards](../Coding_Standards.md) · [ADR register](README.md)

**Architecture**
[Technical Architecture §10](../../02_Architecture/Technical_Architecture.md#10-frontend-architecture) · [System Context](../../02_Architecture/System_Context.md) · [Enterprise Architecture](../../02_Architecture/Enterprise_Architecture.md)

**Related decisions**
[ADR-0004 — Repository, service, router](ADR-0004-repository-service-router.md) · [ADR-0008 — Advisory AI](ADR-0008-advisory-ai-never-auto-release.md) · [ADR-0009 — Modular monolith first](ADR-0009-modular-monolith-before-services.md)

**Repository root**
[README](../../../README.md) · [VISION](../../../VISION.md) · [ROADMAP](../../../ROADMAP.md) · [CONTRIBUTING](../../../CONTRIBUTING.md) · [SECURITY](../../../SECURITY.md)

---

*Mercury Technologies — One Digital Thread. One Digital Aircraft Passport. One Aviation Enterprise Operating System.*
