# Marketplace Standards

| Field | Value |
|-------|--------|
| Document | Marketplace Standards |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Marketplace Standards for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
Trust, verification, isolation, honest capability claims.

## 3. Normative requirements
- Publisher verification before listing.
- Listings declare required permissions and data access.
- No scraping of tenant data for recommendations without entitlement.
- Parts listings require Supplier Verification tier.

## 4. Future
Settlement, ratings abuse controls, geographic eligibility.

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
