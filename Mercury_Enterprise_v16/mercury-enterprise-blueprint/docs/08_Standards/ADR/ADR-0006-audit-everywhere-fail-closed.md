# ADR-0006 — Audit everywhere, fail closed, evidence append-only

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-08-14 |
| Deciders | Lead architect, security lead, compliance lead |
| Affects | [Audit](../../06_Security/Audit.md) · [Digital Signatures](../../06_Security/Digital_Signatures.md) · [Data Model](../../04_Data/Data_Model.md) · [Digital Thread](../../04_Data/Digital_Thread.md) · [API Standards](../API_Standards.md) · [Coding Standards](../Coding_Standards.md) |
| Canonical slug | `ADR-0006-audit-everywhere-fail-closed.md` |
| Legacy companion | `ADR-0005-immutable-audit-and-history.md` (same immutability decision family) |
| Supersedes | — |
| Superseded by | — |

---

## Context

Airworthiness is established by records. Not by the current state of an aircraft, and not by anyone's recollection — by the documented, attributable, dated evidence that specific work was performed by qualified people under specific instructions and inspected as required. A platform that holds those records has one obligation above all others: **it must not lose or alter them.**

This has consequences that ordinary business software does not face:

1. **History is not metadata; history is the product.** Which parts were installed on this aircraft and when, who signed each step, what revision was in force, how stock arrived and left — these are not an audit trail attached to the real data. In aviation they *are* the real data.

2. **A record's past states matter as much as its present state.** An `UPDATE` that overwrites a component's installation position destroys the fact that it was somewhere else. A conventional mutable row is therefore the wrong model for anything that participates in the [Digital Thread](../../04_Data/Digital_Thread.md).

3. **Deletion is nearly always wrong, and sometimes impossible.** A cancelled purchase order is a fact. A superseded maintenance programme revision is what authorised work performed under it. A record that other records reference cannot vanish without breaking the thread.

4. **Retention horizons are measured in decades.** The life of the asset plus an authority-required period. Software that assumes data can be pruned when it becomes inconvenient is not fit for the domain.

5. **An unaudited safety-relevant act must not exist.** If a certification signature is written and its audit record is not, the platform has evidence of a signature with no record of the act — the opposite of what audit is for.

The decision therefore has to cover three related but distinct mechanisms — immutable evidence, append-only history, and soft delete — and to be **explicit about what is genuinely enforced versus what rests on discipline.** Overstating integrity in this area would be worse than having weaker integrity honestly described, because a customer's compliance argument would be built on it.

---

## Decision

**Evidence records are immutable. History records are append-only. Records that other records reference are retired by status transition or soft delete, never removed. And a required audit write is inside the business transaction, so an unaudited act cannot commit.**

### 1. Immutable evidence — never updated, never deleted

| Record type | Rule |
|-------------|------|
| Audit records | Never updated, never deleted by any code path |
| Digital signatures | Immutable once recorded |
| Certification events | Immutable once recorded |
| Technical logbook entries | **Append-only.** A correction is a new amendment entry that preserves and references the original |
| Publication revisions | Immutable once issued; a new revision supersedes rather than edits |
| Stock movements | Append-only ledger; balances are a maintained summary of it |
| Component history entries | Append-only |

**No service method updates or deletes any of these.** There is no administrative override, no correction endpoint, and no "fix the typo" path. A wrong logbook entry is corrected by appending an amendment, exactly as a paper record is corrected by a dated annotation rather than by erasure.

### 2. Append-only ledgers — every state change writes a row

**Every change to stock state writes a movement row.** There is no code path that alters a balance without a corresponding ledger entry. The movement table is the truth; balances are a maintained summary of it. The same principle governs component history and certification events.

This is what makes inventory **auditable** rather than merely current: a balance can be reconstructed from its movements, and a discrepancy between the two is detectable.

### 3. Atomic evidence creation

On the `aircraft_released` certification step — and only then — a technical logbook entry is written **in the same transaction** as the release signature, together with the component's maintenance-release history entry.

**This atomicity is non-negotiable.** A release without its logbook entry is an unrecorded release. There is no acceptable window — not milliseconds — in which one exists without the other. Any future architectural change that separates them must provide an equivalent guarantee, not an eventual one.

### 4. Fail-closed audit on safety-relevant paths

Audit records for significant transitions are written **by the service, inside the business transaction**. A failed required audit write rolls back the operation it was recording.

The one deliberate exception is the middleware-level API-access audit, which is written after the response in its own session and whose failure is logged without failing the request. This is an availability trade-off, taken knowingly: **a failing audit writer must not stop a technician from signing work.** Its cost — that a persistent audit-writer failure could leave a gap in access logging — is why a durable at-least-once path is a roadmap item rather than a refinement.

### 5. Soft delete and status retirement instead of deletion

| Mechanism | Where | Position |
|-----------|-------|----------|
| `deleted_at` column on retirable records | Warehouses, part masters, tools, maintenance programmes, MPD tasks, maintenance checks | **Current** |
| Every query filtering `deleted_at IS NULL`, in the repository | All of the above | **Current** |
| An endpoint that sets `deleted_at` | — | **Planned.** None exists; nothing in the runtime soft-deletes anything today |
| Retirement in practice | Status transition: `cancelled`, `closed`, `scrapped`, `returned` | **Current** |
| Soft delete on evidence tables | — | **Never.** Evidence tables have no delete concept at all, conventional or otherwise |

Building the read filter before the write path was deliberate: it means adding a delete endpoint cannot accidentally resurrect deleted rows into existing screens.

### 6. Optimistic concurrency, not last-write-wins

Mutable aggregates — work packages, work orders, job cards, maintenance tasks — carry an integer `version` counter incremented on every state change. A caller may supply an expected version; a mismatch aborts with `409`. **The client's correct response is to re-read and retry, never to force.**

---

## Consequences

### Positive

| Consequence | Detail |
|-------------|--------|
| **Evidence is trustworthy against accidental loss** | No code path can overwrite a signature, a logbook entry, or a movement |
| **History is complete by construction** | Not by a change-tracking feature that might be disabled |
| **Inventory is auditable, not merely current** | A balance is reconstructable from its ledger, and drift is detectable |
| **Corrections are visible as corrections** | An amendment preserves the original, which is what an auditor needs and what paper practice already does |
| **The thread never breaks** | A referenced record cannot disappear, so a traversal from 2019 still resolves |
| **Retention obligations are satisfiable** | Nothing is silently pruned |
| **Concurrent edits fail loudly** | Version conflicts surface as `409` rather than as one technician's work silently overwriting another's |
| **An unaudited safety-relevant act cannot commit** | Fail-closed audit makes this structural on the paths that matter most |

### Negative

| Consequence | Mitigation |
|-------------|-----------|
| **Data grows monotonically and is never reclaimed** | Time partitioning of movements, audit, certification events, and logbook entries is planned; an archive tier follows |
| **Ledger tables become the largest in the platform** | Indexed by organization and time, which is how they are queried; partitioning is the scaling answer |
| **Offset pagination over an append-only ledger can skip or repeat rows** | Cursor pagination for ledgers is a named enhancement in [API Standards §5.1](../API_Standards.md#51-pagination) |
| **A genuine data-entry error is permanent** | Deliberate. It is corrected by amendment, which is more honest than erasure. Operationally this raises the importance of confirmation before signing — see [UI Standards §8.3](../UI_Standards.md#83-confirmation-patterns) |
| **Erasure requests conflict with retention** | A real tension. Airworthiness attribution requires retaining who performed maintenance; the retention rules are documented, and field-level encryption of personal data is a named roadmap item. This cannot be resolved by deleting evidence |
| **Retention configuration hides rather than deletes** | The retention window is a **query filter**, not a lifecycle. An operator who must genuinely delete after a period cannot achieve it with this setting alone. Stated in [Audit](../../06_Security/Audit.md) so nobody discovers it during an audit |
| **Fail-closed audit can block a business operation** | Accepted on safety-relevant paths: an unaudited signature is worse than a failed signature the user can retry |
| **Soft delete is half built** | The read filter exists and the write path does not. Honest position rather than an implied capability |

### Operational

- Database growth is a planned operational concern, not an anomaly. Capacity planning assumes monotonic growth.
- Backup and recovery objectives are deliberately asymmetric: **RPO 0 for evidence**, fifteen minutes for transactional data. Fifteen minutes of lost stock movements can be recovered by a physical count; a lost release signature cannot be recovered at all.
- A restore that loses evidence is a reportable event, not merely an outage.
- Any bulk data operation — migration, import, remediation — must be reviewed against this ADR before execution, because a bulk `UPDATE` on an evidence table would violate a control that the application otherwise makes impossible.

---

## Alternatives considered

### 1. Mutable records with a database-level change-data-capture or trigger-based audit table

**Rejected as the primary model.** It would give change history with less application code. Rejected because the audit table becomes a technical artefact rather than a domain record: it captures column-level before-and-after values, not the **business act** with its actor, purpose, and outcome. An auditor asking "who released this aircraft and under what authority" is poorly served by a row-diff log. Mercury's audit is a first-class domain record for exactly this reason — see [Audit §1.2](../../06_Security/Audit.md#12-audit-is-not-logging).

### 2. Hard delete with archival to a separate store before deletion

**Rejected.** It bounds table growth, which is the genuine attraction. Rejected because it introduces a window in which a record exists in neither place, because it breaks referential integrity within the thread, and because the archive becomes a second source of truth whose completeness is impossible to demonstrate. The failure mode — an archive that silently missed rows — is undetectable, which is the worst property an evidence store can have.

### 3. Full temporal tables — system-versioned history for every table

**Considered seriously, rejected as universal.** Complete history for everything, maintained by the database, is elegant. Rejected because it applies uniform cost to records where it adds nothing (a warehouse's address history is not evidence), because query complexity rises across the board, and because the domain's genuine history requirements are already met by the ledger and evidence model. Applying it selectively would produce two history mechanisms, which is worse than one applied deliberately.

### 4. Event sourcing as the primary model

**Rejected.** Addressed in [ADR-0002](ADR-0002-digital-thread-as-spine.md). Mercury takes the valuable part — append-only ledgers and immutable evidence where history is the point — without adopting event sourcing for the whole domain.

### 5. Best-effort audit everywhere, never fail-closed

**Rejected for safety-relevant paths.** It maximises availability and it is what most systems do. Rejected because an unaudited certification signature or stock movement is precisely the record whose absence would matter in an investigation. The trade-off is made **selectively**: fail-closed for domain acts, best-effort for the middleware access log, with the reasoning for each stated where it applies.

### 6. Database-enforced append-only from the start — triggers or permission-level controls

**Deferred, not rejected. This is the intended strengthening, and it is the most important item in the roadmap for this ADR.** Today immutability rests on **code discipline**: no service method updates or deletes evidence, verified by review and tests. That is a strong convention and it is honestly labelled as one — a sufficiently privileged database credential could alter a signature row and, because the digest is over content the same actor controls, recompute its hash. Making immutability structural requires a database permission model and trigger design that must be got right, and it interacts with the partitioning and hash-chaining work. It is sequenced accordingly rather than skipped.

### 7. Tamper-evident hash chaining across audit and evidence records

**Deferred, planned, and named as the highest-value integrity upgrade available to the platform.** Each record carrying a hash of its predecessor would make undetected alteration or deletion of an interior record infeasible. It requires a defined sequence, which interacts with time partitioning and must be designed together with it, and it is most valuable combined with external anchoring of periodic checkpoints so integrity is verifiable by a third party rather than only by Mercury.

---

## Compliance and security impact

| Concern | Impact |
|---------|--------|
| **Isolation** | Evidence records carry `organization_id` and are queried under the same scoping rules as everything else. Immutability does not create a cross-tenant read path. See [ADR-0003](ADR-0003-org-isolation-multitenancy.md) |
| **RBAC** | Reading the audit trail is a permission in its own right, held by reviewer and administrator roles. No role has permission to alter evidence, because no such capability exists to grant |
| **Audit** | This ADR defines the audit integrity model: first-class domain records, immutable, fail-closed on safety-relevant paths, with the middleware exception documented |
| **Signatures** | A signature's integrity claim depends on this model. The SHA-256 digest over a canonical payload proves the recorded content is unaltered **through the application**; immutability by discipline is what stops the application altering it. The cryptographic limits are stated in [ADR-0006](ADR-0006-hash-signatures-before-pki.md) |
| **Regulatory evidence** | Directly supports the expectations that maintenance actions are attributable, that records establish what authorised them, that independence of inspection is demonstrable, and that records are protected from unauthorized alteration — the last of which is honestly **Partial**, because protection is conventional rather than structural |
| **Data protection** | The most difficult tension in the platform. Evidence permanently links named individuals to acts, which is an airworthiness requirement, so an erasure request cannot be satisfied by deleting evidence. Retention rules are documented; field-level encryption of personal data is planned; the conflict is stated rather than glossed |
| **Honest limitations** | Stated plainly and repeated because they are the most important sentences in this ADR: immutability is **conventional, not structural**; there is **no hash chaining**, so deleting an entire signature and its certification event leaves a gap detectable by workflow reasoning but not by cryptography; retention **hides rather than deletes**; and the middleware audit path is **best-effort**. Each appears in [SECURITY.md](../../../SECURITY.md) and none is disguised |

---

## Related documents

**Security and evidence**
[Audit](../../06_Security/Audit.md) · [Digital Signatures](../../06_Security/Digital_Signatures.md) · [RBAC](../../06_Security/RBAC.md) · [Identity](../../06_Security/Identity.md) · [SECURITY.md](../../../SECURITY.md)

**Data**
[Data Model](../../04_Data/Data_Model.md) · [Digital Thread](../../04_Data/Digital_Thread.md) · [Master Data](../../04_Data/Master_Data.md)

**Architecture**
[Technical Architecture §9](../../02_Architecture/Technical_Architecture.md#9-consistency-concurrency-and-transactions) · [Domain Architecture](../../02_Architecture/Domain_Architecture.md)

**Standards**
[API Standards §5.5](../API_Standards.md#55-soft-deleted-records) · [Coding Standards §10.4](../Coding_Standards.md#104-rules-for-changing-an-existing-table) · [UI Standards](../UI_Standards.md)

**Business context**
[Authority](../../03_Business/Authority.md) · [CAMO](../../03_Business/CAMO.md) · [MRO](../../03_Business/MRO.md) · [Leasing](../../03_Business/Leasing.md)

**Related decisions**
[ADR-0002 — Digital Thread as the spine](ADR-0002-digital-thread-as-spine.md) · [ADR-0003 — Organization isolation](ADR-0003-org-isolation-multitenancy.md) · [ADR-0006 — Hash signatures before PKI](ADR-0006-hash-signatures-before-pki.md) · [ADR-0007 — Logistics as an integrated program](ADR-0007-logistics-as-integrated-program.md)

---

*Mercury Technologies — One Digital Thread. One Digital Aircraft Passport. One Aviation Enterprise Operating System.*
