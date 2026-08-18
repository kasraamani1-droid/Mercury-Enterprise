# Database Standards

| Field | Value |
|-------|--------|
| Document | Database Standards |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Database Standards for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
PostgreSQL OLTP as system of record; org_id on tenant data; immutable history tables; Alembic only schema path.

## 3. Normative requirements
- Surrogate string PKs; explicit FKs; composite indexes for org+status+time.
- Soft delete via `deleted_at` or status — never hard-delete audit/signature/movement rows.
- Numeric quantities as Decimal/Numeric; booleans as documented string flags where legacy Mercury pattern applies — new work prefers native boolean only with migration plan.
- Ban N+1: repository query shapes with joins/eager load as needed.

## 4. Scalability / Security
Partitioning candidates for movements/audit by time; encryption at rest by platform; least-privilege DB roles.

---

## 6. Non-functional requirements

Traceability, reviewability, and operability appropriate to safety-adjacent enterprise software. Changes that alter normative rules require ADR or standards PR with CHANGELOG entry.

---

## 7. Security considerations

No standard may weaken organization isolation, RBAC, or fail-closed audit without an explicit superseding ADR.

---

## 8. Scalability considerations

Standards must remain implementable on the modular monolith and remain valid when contexts are extracted.

---

## 9. Related documents

[ADR Index](ADR/README.md) · [Coding Standards](Coding_Standards.md) · [API Standards](API_Standards.md) · [Technical Architecture](../02_Architecture/Technical_Architecture.md)
