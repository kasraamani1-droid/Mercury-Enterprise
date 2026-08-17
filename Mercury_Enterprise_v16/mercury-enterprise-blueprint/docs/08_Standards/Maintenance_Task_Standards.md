# Maintenance Task Standards

| Field | Value |
|-------|--------|
| Document | Maintenance Task Standards |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Maintenance Task Standards for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
Single maintenance task engine for certify actions; job cards reference tasks; planning uses MPD definitions.

## 3. Normative requirements
- Task intervals multi-unit (FH/FC/calendar/…).
- Sign actions audited; skill/cert gates enforced in service.
- Required parts/tools text must be plannable into logistics bridges.

## 4. Related
Planning docs · Work order docs · Logistics material planning.

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
