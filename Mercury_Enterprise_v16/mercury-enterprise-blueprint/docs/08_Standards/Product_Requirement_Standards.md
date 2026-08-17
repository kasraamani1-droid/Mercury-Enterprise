# Product Requirement Standards

| Field | Value |
|-------|--------|
| Document | Product Requirement Standards |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Product Requirement Standards for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
Requirements must state Digital Thread impact, security impact, and honesty of delivery status.

## 3. Normative PRD / APPLY_TASK sections
1. Problem and persona 2. Scope / non-scope 3. Entities & APIs 4. Workflows 5. **Digital Thread impact** 6. RBAC/audit 7. Data migration 8. Acceptance tests 9. Docs to update 10. Status Delivered/Partial/Planned after ship

## 4. Forbidden
Fake UAT; requirements that skip SoD; AI auto-approve language.

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
