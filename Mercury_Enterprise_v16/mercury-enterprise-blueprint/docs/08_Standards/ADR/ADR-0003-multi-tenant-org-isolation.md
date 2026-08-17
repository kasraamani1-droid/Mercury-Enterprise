# ADR-0003 — Multi-tenant organization isolation enforced in the service layer

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-08-14 |
| Deciders | Lead architect, security lead, data architect |
| Affects | [RBAC](../../06_Security/RBAC.md) · [Identity](../../06_Security/Identity.md) · [Data Model](../../04_Data/Data_Model.md) · [Technical Architecture](../../02_Architecture/Technical_Architecture.md) · [API Standards](../API_Standards.md) · [Coding Standards](../Coding_Standards.md) |
| Canonical slug | `ADR-0003-multi-tenant-org-isolation.md` |
| Legacy slug | `ADR-0003-org-isolation-multitenancy.md` |
| Supersedes | — |
| Superseded by | — |

---

## Context

Mercury serves aircraft manufacturers, airlines, MRO organizations, CAMO organizations, component shops, warehouses, suppliers, lessors, and authorities — frequently **several of them on the same platform instance, with legitimate relationships between them.** An MRO performs work on an aircraft an airline operates and a lessor owns. A CAMO manages continuing airworthiness for an operator. A supplier ships parts into an MRO's stores.

This makes tenancy harder than the usual software-as-a-service case in three specific ways:

1. **The boundary is legal and regulatory, not merely commercial.** An organization is an operating entity with its own approvals, its own certifying staff, and its own accountability to an authority. Data crossing that boundary without authorization is not an inconvenience; it can be a regulatory breach and a commercial catastrophe.

2. **Users legitimately belong to more than one organization, with different authority in each.** The same person may be an operator in one organization and a viewer in another. Their effective role must derive from their **membership in the active organization**, not from a global directory entry.

3. **Cross-organization visibility is a real requirement, not an anti-pattern.** A lessor needs asset condition on aircraft an operator flies. An authority needs oversight-ready evidence. These are legitimate needs that must be served **explicitly and auditably** rather than by relaxing isolation.

The available isolation models — database per tenant, schema per tenant, or a shared schema with a discriminator column — each trade operational cost against isolation strength. Mercury also had to decide **where** isolation is enforced, which turns out to matter more than which model is chosen: a perfect model enforced in a router that a future endpoint forgets to use is worse than a modest model enforced where it cannot be omitted.

---

## Decision

**Adopt a shared-schema multi-tenancy model in which every tenant-owned table carries an indexed, non-nullable `organization_id` column, and enforce isolation in the service and repository layers — never in the router, never in the client.**

The model has five mandatory components:

### 1. The column

Every tenant-owned table carries `organization_id`, indexed, never nullable in a new table:

```python
organization_id: Mapped[str] = mapped_column(String(80), index=True)
```

Business keys are unique **within** an organization, never globally:

```python
__table_args__ = (UniqueConstraint("organization_id", "code", name="uq_log_wh_org_code"),)
```

### 2. Resolution and assertion in the service

Every tenant-aware service exposes and uses two members. **The first statement of every tenant-aware service method resolves the organization.**

```python
def resolve_org_id(self, actor: ActorContext, requested_org_id: str | None = None) -> str:
    org_id = (requested_org_id or actor.organization_id or "").strip()
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization is required")
    self.org.assert_org_access(username=actor.username, session_role=actor.role, organization_id=org_id)
    return org_id
```

| Behaviour | Result |
|-----------|--------|
| No organization requested | The session's active organization is used |
| An organization requested and the caller is entitled | That organization is used |
| An organization requested and the caller is **not** entitled | `403` — the assertion is refused, disclosing nothing about that organization's contents |
| Empty or whitespace | `400 Bad Request` |

**A client-supplied organization is never trusted without verification.** This is the whole point of the function.

### 3. The filter in the repository

Every repository method takes the resolved organization and filters on it. The filter is in the repository specifically **so that a caller cannot forget it**:

```python
def get_part(self, organization_id: str, part_id: str, *, for_update: bool = False) -> PartMaster | None:
    stmt = select(PartMaster).where(
        PartMaster.id == part_id,
        PartMaster.organization_id == organization_id,
        PartMaster.deleted_at.is_(None),
    )
    ...
```

A repository method without a tenancy filter is a tenancy defect regardless of how carefully its callers behave.

### 4. Two independent gates, always both

| Gate | Question | Where |
|------|----------|-------|
| **Gate 1 — endpoint permission** | May this role call this endpoint at all? | Router dependency, coarse |
| **Gate 2 — organization access** | May this user act on this organization's data? | Service, and this is the tenancy control |

**Neither substitutes for the other.** A permission grant is not organization access, and organization membership is not a permission. Signing adds a third, separate gate — see [ADR-0006](ADR-0006-hash-signatures-before-pki.md) and [Digital Signatures](../../06_Security/Digital_Signatures.md).

### 5. `404`, not `403`, for another organization's records

| Caller action | Result | Reason |
|---------------|--------|--------|
| Explicitly requests an organization they may not act in | `403` | They asserted an entitlement they do not hold. Refusing the assertion reveals nothing about that organization |
| Requests a record by identifier that belongs to another organization | **`404`** | The query was organization-scoped, so the record is not there — indistinguishable from a bad identifier |

The second behaviour is a deliberate isolation measure: a `403` would confirm that the identifier exists **somewhere** in the platform, which is a cross-tenant enumeration channel. Both behaviours are tested; the second must not be "improved" into a `403`.

### 6. Cross-organization access is explicit and audited

Only the administrator role may cross organizations, and **every crossing writes an audit record**. Context switching re-verifies membership, re-derives the effective role from membership in the target organization, validates that the organization has a usable site, and audits both success and denial.

---

## Consequences

### Positive

| Consequence | Detail |
|-------------|--------|
| **Isolation cannot be forgotten** | The filter is in the repository and the assertion is in the service; there is no path to tenant data that bypasses both |
| **Enforcement is auditable in one place per module** | A security review reads the service layer. See [ADR-0004](ADR-0004-repository-service-router.md) |
| **Cross-tenant identifiers are not probeable** | The `404` rule closes the enumeration channel |
| **Operational simplicity** | One schema, one migration run, one connection pool, one backup regime. A schema-per-tenant model would multiply all four |
| **Cross-organization relationships are expressible** | Which the domain genuinely requires; a hard physical boundary would make lessor and authority visibility impossible without integration |
| **Roles are per organization, which matches reality** | The same person can be an operator in one organization and a viewer in another |
| **Efficient at scale** | The organization index is the highest-value index in the platform, and composite indexes pair it with the common filters |
| **Onboarding a tenant is a data operation, not an infrastructure one** | No provisioning step, no per-tenant migration drift |

### Negative

| Consequence | Mitigation |
|-------------|-----------|
| **A missing filter is a cross-tenant data leak** | The most serious defect class in the platform. Mitigated by the repository-level filter, the mandatory tenancy test per module, and a standing review item. **Planned:** PostgreSQL row-level security as a structural backstop, so a missed filter fails rather than leaks |
| **Isolation is logical, not physical** | A sufficiently privileged database credential sees every tenant. Stated honestly; no shared-schema model can claim otherwise |
| **A noisy tenant affects others** | Shared connection pool and shared tables. Mitigated by clamped pagination and indexed filters; per-tenant quotas are a future item |
| **Bulk operations must be organization-scoped line by line** | Enforced in the service; a bulk line naming another organization's record is rejected, not silently skipped |
| **The administrator role is powerful** | Wildcard permission plus cross-organization access. Mitigated by auditing every crossing. **Debt:** an administrator's cross-tenant *read* is not yet audited as thoroughly as a write — named in [Audit](../../06_Security/Audit.md) |
| **Per-tenant data residency is not achievable in one instance** | A jurisdictional requirement would need a separate deployment. Acknowledged rather than solved |
| **Every new table adds the column, the index, and the test** | Repetitive by design. A shared base class is a candidate enhancement, weighed against the explicitness the repetition currently provides |

### Operational

- Tenant data export and deletion are query-scoped operations, which makes them feasible but also means they must be written carefully: an export missing a table silently under-delivers.
- Backup and restore are all-tenant operations. Restoring one tenant to a point in time requires a selective restore procedure, which is an operational gap worth naming.
- The organization index must exist on every new tenant table before that table sees production volume; adding it later on a large table is an operational event.

---

## Alternatives considered

### 1. Database per tenant

**Rejected.** The strongest isolation available and genuinely attractive for a regulated domain: a missing filter cannot leak because there is nothing to leak into. Rejected because it makes cross-organization relationships — lessor visibility, authority oversight, MRO working on an operator's aircraft — require cross-database integration, which is the platform's core value proposition made expensive. It also multiplies migration risk by the tenant count, prevents shared reference data, and makes onboarding an infrastructure operation. **This is the alternative Mercury would revisit** if a customer arrived with a hard physical-isolation or data-residency requirement, and it would be served by a separate deployment rather than by changing this model.

### 2. Schema per tenant in one database

**Rejected.** A middle position that keeps one database while giving each tenant its own tables. Rejected because it inherits most of the migration multiplication of option 1 — every schema change runs per schema, and drift between schemas is a real operational failure mode — while providing isolation that is still ultimately logical, since one credential can reach every schema. Cross-organization queries also become awkward without delivering a genuinely stronger boundary.

### 3. Shared schema with PostgreSQL row-level security as the primary control

**Deferred, not rejected — and this is the intended future strengthening.** Row-level security would make isolation structural: a session variable carries the organization, and the database refuses rows outside it, so a missing application filter fails closed instead of leaking. It was not adopted as the *primary* control initially because the application must still resolve entitlement (the database cannot know whether a user may act in an organization), because the session-variable lifecycle interacts with connection pooling in ways that need careful handling, and because it would have delayed delivery of the domain. **The correct end state is both**: application enforcement as the decision, row-level security as the backstop. It is a named enhancement.

### 4. Tenancy in the session only, with no explicit parameter

**Rejected.** Simpler, and it would remove the class of defect where a client-supplied organization is trusted. Rejected because cross-organization work is a genuine requirement: an administrator investigating an issue, a lessor reading asset condition, a group-level user working across subsidiaries. Removing the parameter would force context switching for every such read, which is worse operationally and produces a coarser audit trail than an explicit, verified parameter.

### 5. Enforce tenancy in middleware

**Rejected.** Attractive because it appears to be a single choke point. Rejected because middleware cannot know which records a request will touch, so it can only validate the *declared* organization — not that every query actually filtered on it. It would provide the appearance of a single control while the real filtering remained distributed, which is the worst of both positions.

### 6. `403` rather than `404` for another organization's records

**Rejected.** More honest in a narrow sense, and easier to debug. Rejected because it confirms the existence of an identifier across a tenancy boundary, which lets a caller enumerate the platform's contents. The debugging cost is real and is paid deliberately.

---

## Compliance and security impact

| Concern | Impact |
|---------|--------|
| **Isolation** | This ADR *is* the isolation model. Its strength rests on two independent controls — the service-layer assertion and the repository-layer filter — plus the non-probeability rule. Its honest limit is that isolation is logical: a privileged database credential sees everything |
| **RBAC** | The effective role is derived from **membership in the active organization**, not from the login directory. A context switch re-derives it and audits the switch. Permission and organization access remain independent gates |
| **Audit** | Every cross-organization act is audited, including denied switches as security events. **Debt:** administrator cross-tenant reads are under-audited relative to writes — named in [Audit](../../06_Security/Audit.md) |
| **Signatures** | The signing employee must exist **in the task's organization** and be active; a signer from another organization is refused at `404` or `403`, never accepted. Tenancy is therefore part of the certification gate, not merely of data access |
| **Enumeration resistance** | The `404` rule is the control. Error messages must never distinguish "exists elsewhere" from "does not exist" — including in validation messages, which is an easy place to leak |
| **Regulatory evidence** | An organization's records are attributable to that organization's approvals and certifying staff. Cross-organization data appearing in an evidence pack would undermine the pack; the scoping rules prevent it |
| **Data protection** | Tenant data export and erasure are query-scoped and therefore feasible, subject to the airworthiness retention obligations described in [ADR-0005](ADR-0005-immutable-audit-and-history.md). Per-tenant data residency is **not** achievable within one instance |
| **Known debt** | No row-level security backstop; logical rather than physical isolation; a powerful administrator role; under-audited cross-tenant reads; no per-tenant resource quotas. All are recorded in [SECURITY.md](../../../SECURITY.md) |

---

## Related documents

**Security**
[RBAC](../../06_Security/RBAC.md) · [Identity](../../06_Security/Identity.md) · [Audit](../../06_Security/Audit.md) · [Digital Signatures](../../06_Security/Digital_Signatures.md) · [SECURITY.md](../../../SECURITY.md)

**Architecture and data**
[Technical Architecture §4](../../02_Architecture/Technical_Architecture.md#4-tenancy-and-authorization-enforcement) · [Domain Architecture](../../02_Architecture/Domain_Architecture.md) · [System Context](../../02_Architecture/System_Context.md) · [Data Model](../../04_Data/Data_Model.md) · [Master Data](../../04_Data/Master_Data.md)

**Standards**
[API Standards §7](../API_Standards.md#7-authentication-authorization-and-organization-scoping) · [Coding Standards §5](../Coding_Standards.md#5-backend-layer-conventions) · [UI Standards](../UI_Standards.md)

**Business context**
[Airline](../../03_Business/Airline.md) · [MRO](../../03_Business/MRO.md) · [CAMO](../../03_Business/CAMO.md) · [Leasing](../../03_Business/Leasing.md) · [Authority](../../03_Business/Authority.md)

**Related decisions**
[ADR-0002 — Digital Thread as the spine](ADR-0002-digital-thread-as-spine.md) · [ADR-0004 — Repository, service, router](ADR-0004-repository-service-router.md) · [ADR-0005 — Immutable audit and history](ADR-0005-immutable-audit-and-history.md) · [ADR-0009 — Modular monolith first](ADR-0009-modular-monolith-before-services.md)

---

*Mercury Technologies — One Digital Thread. One Digital Aircraft Passport. One Aviation Enterprise Operating System.*
