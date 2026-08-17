# ADR-0004 — Adopt the repository, service, thin-router layered module pattern

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-08-14 |
| Deciders | Lead architect, security lead |
| Affects | [Technical Architecture](../../02_Architecture/Technical_Architecture.md) · [Domain Architecture](../../02_Architecture/Domain_Architecture.md) · [Coding Standards](../Coding_Standards.md) · [API Standards](../API_Standards.md) |
| Supersedes | — |
| Superseded by | — |

---

## Context

Mercury has nine domain modules — `org`, `fleet`, `components`, `publications`, `personnel`, `maintenance`, `work_orders`, `planning`, `logistics` — and will have more. They call each other constantly: planning calls work orders and logistics; work orders calls maintenance, publications, and personnel; every module calls organizations to assert tenancy.

Two properties are non-negotiable for this platform:

1. **A safety review must be tractable.** A reviewer asking "where is the rule that prevents an unqualified person signing an independent inspection" must have one place to look. If domain rules are distributed across routers, models, services, and validators, the answer is "read the codebase", which means the review does not happen properly.

2. **Tenancy and authorization cannot be optional.** Isolation under [ADR-0003](ADR-0003-org-isolation-multitenancy.md) depends on every path to tenant data passing through both an entitlement assertion and an organization-filtered query. A structure that allows a path to bypass either is an isolation defect waiting for a hurried change.

The failure modes this decision exists to prevent are all ones that FastAPI makes easy:

- **Business logic in the router.** A route with a database session and a `select()` can implement a whole feature in one function. It works, and it is invisible to a reviewer looking for rules in the service layer.
- **Decisions in the repository.** A query method that also raises `404`, or checks a status, has taken a decision the domain layer should own — and it will be inconsistent with the same decision elsewhere.
- **Cross-module table access.** One module querying another's tables is the fastest way to deliver a feature and the fastest way to bypass the owning module's invariants. It also destroys any possibility of later extraction.
- **Business rules in the model.** Validation and lifecycle logic on a SQLAlchemy model spreads decisions into a layer whose job is mapping.

The pattern also had to serve a longer-term option: keeping **service extraction available** without paying for a distributed architecture now. See [ADR-0009](ADR-0009-modular-monolith-before-services.md).

---

## Decision

**Every domain module is a Python package with the same six files, and the layers have strict, reviewable responsibilities. The governing rule: a router never touches the database, and a repository never makes a decision.**

```text
backend/app/<domain>/
├── __init__.py      Lazy export of the service class; avoids import cycles
├── models.py        SQLAlchemy models — tables, columns, indexes, constraints
├── schemas.py       Pydantic request and response contracts
├── repository.py    Query and persistence access; no business rules
├── service.py       Domain logic, invariants, tenancy assertion, transactions
└── router.py        APIRouter with prefix, tags, permission dependencies
```

### Layer responsibilities and prohibitions

| Layer | Owns | Must never |
|-------|------|-----------|
| **Router** | HTTP verbs and paths, status codes, permission dependencies, request and response schemas | Contain business rules, query the database, or construct models |
| **Service** | Domain invariants, organization resolution and assertion, cross-module calls, the transaction boundary, audit writes | Deal in HTTP concepts beyond raising typed errors; reach into another module's tables |
| **Repository** | Queries, filters, ordering, pagination clamps, locking, flush, refresh | Contain business rules or make authorization decisions |
| **Model** | Table, column, index, constraint, and relationship definitions | Contain business logic |
| **Schema** | Request validation and response shaping | Contain business logic or query the database |

### Import rules

| File | May import | Must never import |
|------|-----------|-------------------|
| `models.py` | `database`, shared model helpers | Schemas, service, router |
| `schemas.py` | Standard library, Pydantic | Models, repository, service |
| `repository.py` | Own models | Service, router, another module's models |
| `service.py` | Own models, schemas, repository; peer module **services** | Another module's models or repository |
| `router.py` | Own schemas and service, security, database | Own models, own repository |

### Cross-module access

**A module reaches another domain only through that domain's service class, constructed with the same database session.**

```python
# planning/service.py — generating a work package
work_orders = WorkOrderService(self.db)
package = work_orders.create_package(...)
order = work_orders.create_order(...)

logistics = LogisticsService(self.db)          # imported at call time to break the cycle
result = logistics.run_material_planning(...)
```

This has three consequences that are the point of the rule:

1. **The peer module's invariants are applied.** There is no bypass, because the only entry point is the public method that enforces them.
2. **Everything is in one transaction.** The shared session means the whole operation commits or rolls back together — which is what the atomicity requirements in [ADR-0002](ADR-0002-digital-thread-as-spine.md) and [ADR-0005](ADR-0005-immutable-audit-and-history.md) demand.
3. **The seam is preserved.** Today's method call is the exact place tomorrow's API call would go.

### The transaction boundary

**The service method owns the transaction.** Routers do not commit. Repositories flush but do not commit. A service either completes its whole operation and commits — through a helper that translates integrity errors to `409` — or raises and rolls back.

---

## Consequences

### Positive

| Consequence | Detail |
|-------------|--------|
| **A safety review reads one layer** | Every domain invariant and every authorization decision is in the service layer. This is the single most valuable property of the pattern |
| **Tenancy cannot be bypassed** | The service asserts entitlement and the repository filters; neither is optional and neither is in a layer a new endpoint can skip |
| **Uniformity across nine modules** | A developer who knows one module knows all of them; a reviewer knows where to look before opening the file |
| **Peer invariants always apply** | Cross-module calls go through the owning service, so a shortcut cannot skip a rule |
| **Extraction stays available** | Module boundaries are maintained as though they were service boundaries. The option has been preserved rather than spent |
| **Testable through the real stack** | Tests exercise router, schema, service, and repository against a real session, with no mocking — which is why the tests are evidence rather than decoration |
| **Thin routers keep the API honest** | A router that only declares its contract and delegates cannot accidentally encode a rule that the API documentation does not describe |
| **Locking and concurrency live where state transitions live** | The service, which is also where the invariant being protected is enforced |

### Negative

| Consequence | Mitigation |
|-------------|-----------|
| **More files and more indirection for simple features** | Accepted deliberately. "The queries are simple" is how a repository gets skipped and how the pattern erodes; simple queries grow |
| **Service classes become large** | Logistics is the extreme case. Mitigated by section banners, private helpers, and splitting by feature area when a file becomes unreadable. The alternative — distributing the rules — is worse |
| **Import cycles between peer modules** | Two established patterns handle it: a lazy `__getattr__` in `__init__.py`, and a call-time import inside the method. Both are documented in [Coding Standards §3.3](../Coding_Standards.md#33-imports) so they are recognised as intentional |
| **Boundaries are convention, not enforcement** | A module *could* import a peer's models; nothing structural prevents it. Mitigated by review and by the explicit import table. **Planned:** an import-linting rule to make the boundary mechanical |
| **Cross-module calls are synchronous and in-transaction** | Which produces the platform's two long transactions. Both are deliberate and documented in [Technical Architecture §12.4](../../02_Architecture/Technical_Architecture.md#124-where-the-monolith-shows) |
| **Repetition of tenancy and lookup helpers per module** | `resolve_org_id` and `_require_<thing>` recur. Accepted: each module owning its own enforcement is a feature, because a shared base class would make it possible to change every module's tenancy behaviour at once |

### Operational

- A new module is a mechanical exercise following the ten-step checklist, which reduces the chance of omitting the organization index, the migration, or the tenancy test.
- Diagnosing a defect starts from the layer that owns the concern: a wrong status code is a router question, a wrong rule is a service question, a slow query is a repository question.
- Onboarding a developer is materially faster than in a codebase where each feature has its own shape.

---

## Alternatives considered

### 1. Fat routers — logic directly in the endpoint function

**Rejected.** It is the fastest way to ship the first twenty endpoints and FastAPI makes it pleasant. Rejected because it makes a safety review intractable: rules would live in whichever endpoint happened to need them, duplicated inconsistently across the endpoints that need the same rule. It also makes cross-module reuse impossible without calling one endpoint's function from another, which is a worse coupling than a service call.

### 2. Active Record — business logic on the SQLAlchemy models

**Rejected.** Familiar from Django and Rails, and genuinely concise for CRUD. Rejected because Mercury's rules are overwhelmingly **cross-aggregate**: a release involves a task, certification events, signatures, a logbook entry, and component history. Logic on a single model class cannot express a rule that spans five tables without one model reaching into others, which reproduces exactly the coupling the pattern exists to prevent. It would also put authorization decisions in the persistence layer.

### 3. Service layer without a repository — services query directly

**Considered seriously, rejected.** This is the most tempting simplification: it removes a file and a layer of indirection, and for a module with a handful of queries it reads better. Rejected for one specific reason that outweighs the ergonomics: **the tenancy filter and the pagination clamp would move into the service, where they are one line in each of forty methods rather than one line in each of forty query builders.** The difference matters because a repository method *cannot be called without its filter*, whereas a service method can forget to add one. The repository is where isolation becomes structural rather than remembered.

### 4. CQRS — separate command and query paths

**Rejected for now.** It would fit the read patterns well: dashboards and the aircraft passport are read models over a write model. Rejected as a *primary* structure because it doubles the pattern count for every module while the domain model is still moving, and because Mercury's writes need to read current state to enforce invariants — which a strict separation complicates. Purpose-built read models for dashboards and the passport are planned as an **optimisation within** this pattern, not as a replacement for it.

### 5. Hexagonal architecture with ports and adapters

**Rejected as over-engineering for the current need.** Full dependency inversion around the domain would make the domain independent of SQLAlchemy and FastAPI, which is theoretically valuable. Rejected because Mercury has no realistic plan to change either — [ADR-0001](ADR-0001-vanilla-js-fastapi-aeos.md) commits to both — so the abstraction would be paid for continuously and exercised never. The layered pattern captures the valuable part (rules in one place, persistence separated) without the interface proliferation.

### 6. Microservices per domain from the start

**Rejected.** Addressed fully in [ADR-0009](ADR-0009-modular-monolith-before-services.md). In short: the atomicity requirements of the release chain would become distributed-saga problems, boundaries drawn into network calls are expensive to redraw while the domain is still moving, and operational simplicity is a safety property.

### 7. Shared base classes for services and repositories

**Partially rejected.** A base repository providing tenancy filtering and pagination generically was considered and is genuinely attractive. It was declined for now because the explicit per-module filter is more readable, because a generic filter is easy to bypass accidentally with a custom query, and because a shared base means a single change can alter every module's isolation behaviour at once — which is exactly the blast radius to avoid in the platform's most security-sensitive mechanism. It remains a candidate if repetition becomes a genuine maintenance problem.

---

## Compliance and security impact

| Concern | Impact |
|---------|--------|
| **Isolation** | **The pattern is what makes [ADR-0003](ADR-0003-org-isolation-multitenancy.md) enforceable.** Assertion in the service and filtering in the repository are two independent controls in two layers, and no path to tenant data avoids both |
| **RBAC** | Gate 1 is a declared router dependency, visible in every route signature. Gate 2 is in the service. The separation means a permission change and a tenancy change are reviewed independently |
| **Audit** | Audit is written by the service, inside the business transaction, so audit and effect commit together. A router-level audit could not participate in the transaction; a repository-level audit would not know the business action |
| **Signatures** | The certification gates — employee validity, signer binding, credential verification, step order, distinct signer — are all service-layer checks in the maintenance module, reached through its service by any caller. A work order releasing a job card cannot skip them, because it calls the maintenance service rather than writing signatures itself |
| **Concurrency as a security control** | Row locking before state transitions lives in the service beside the invariant it protects. Removing a lock for performance is therefore visible as a change to the layer under safety review — and it must be reviewed as a security change |
| **SQL injection** | Structurally prevented: all access is through SQLAlchemy constructs in the repository, parameterised, with no string interpolation |
| **Mass assignment** | Prevented by explicit field allow-lists in service update methods; the schema layer additionally constrains what can arrive |
| **Reviewability** | The strongest security consequence of the pattern: a reviewer can read nine service files and see every rule in the platform. That property must be defended against any convenience that would erode it |
| **Known debt** | Boundaries are maintained by convention rather than by tooling; an import-linting rule is a named enhancement. Contract tests at module boundaries are a prerequisite for any extraction and do not yet exist |

---

## Related documents

**Architecture**
[Technical Architecture §2](../../02_Architecture/Technical_Architecture.md#2-layered-architecture) · [Technical Architecture §3](../../02_Architecture/Technical_Architecture.md#3-module-package-pattern) · [Domain Architecture](../../02_Architecture/Domain_Architecture.md) · [Enterprise Architecture](../../02_Architecture/Enterprise_Architecture.md)

**Standards**
[Coding Standards §4](../Coding_Standards.md#4-module-package-pattern) · [Coding Standards §5](../Coding_Standards.md#5-backend-layer-conventions) · [API Standards](../API_Standards.md) · [UI Standards](../UI_Standards.md)

**Security**
[RBAC](../../06_Security/RBAC.md) · [Audit](../../06_Security/Audit.md) · [Digital Signatures](../../06_Security/Digital_Signatures.md) · [SECURITY.md](../../../SECURITY.md)

**Related decisions**
[ADR-0001 — Vanilla JS and FastAPI](ADR-0001-vanilla-js-fastapi-aeos.md) · [ADR-0003 — Organization isolation](ADR-0003-org-isolation-multitenancy.md) · [ADR-0005 — Immutable audit and history](ADR-0005-immutable-audit-and-history.md) · [ADR-0009 — Modular monolith first](ADR-0009-modular-monolith-before-services.md)

---

*Mercury Technologies — One Digital Thread. One Digital Aircraft Passport. One Aviation Enterprise Operating System.*
