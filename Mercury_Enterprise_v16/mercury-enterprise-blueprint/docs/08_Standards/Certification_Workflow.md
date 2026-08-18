# Certification Workflow Standards

| Field | Value |
|-------|--------|
| Document | Certification Workflow Standards |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Certification Workflow Standards for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
Segregation of duties; publication binding; fail-closed audit; human accountability.

## 3. Normative flow
```mermaid
flowchart LR
  Perform --> Inspect
  Inspect --> II[Independent Inspection]
  II --> ACA[ACA Release]
  ACA --> Logbook
```
- Performed ≠ inspected.
- ACA requires authority and publication revision.
- Job cards bridge to maintenance task engine — no duplicate certify engines.

## 4. Related
[Digital Signatures](../06_Security/Digital_Signatures.md) · [Mercury MRO](../05_Product/products/Mercury_MRO.md)

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
