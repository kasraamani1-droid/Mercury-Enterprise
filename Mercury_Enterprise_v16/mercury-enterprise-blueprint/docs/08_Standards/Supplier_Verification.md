# Supplier Verification

| Field | Value |
|-------|--------|
| Document | Supplier Verification |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Supplier Verification for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
Vendors in logistics are first-class; deeper aviation supplier verification is staged.

## 3. Current (Delivered)
Vendor master: type, certificates metadata, approvals text, contacts, rating, lead time, repair capability flags.

## 4. Planned
Document expiry workflows, accredited shop network, evidence file object store, Marketplace gate.

## 5. Security
Org-scoped vendors; audit on rating changes; no silent cross-tenant vendor directories.

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
