# OEM Integration Standards

| Field | Value |
|-------|--------|
| Document | OEM Integration Standards |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs OEM Integration Standards for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
PLM remains OEM system of record; Mercury holds in-service thread; Connect adapts.

## 3. Normative requirements
- Catalog and alternates foundation.
- SB/AD effectivity feedback Planned.
- No uncontrolled writeback that corrupts OEM PLM.

## 4. Related
[OEM business](../03_Business/OEM.md) · [Mercury OEM](../05_Product/products/Mercury_OEM.md) · Connect.

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
