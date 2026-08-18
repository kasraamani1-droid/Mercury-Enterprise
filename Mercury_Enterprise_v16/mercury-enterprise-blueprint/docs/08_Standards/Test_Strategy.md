# Test Strategy

| Field | Value |
|-------|--------|
| Document | Test Strategy |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Test Strategy for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
Prefer API-level tests that prove isolation, RBAC, and thread integrity. Matrices for certification and logistics.

## 3. Normative requirements
- `pytest` backend suite; TestClient with real schema seed.
- Mandatory classes: authz deny paths, cross-org 403, audit presence on critical mutations, migration upgrade path.
- Logistics: FIFO/FEFO, reservation oversell, MR/PO flows; Planning: WP generate bridge; WO: SoD inspect/release.

## 4. Coverage expectations
No vanity % gate that encourages junk tests; critical modules must have explicit scenario catalogs.

## 5. Future
E2E browser suite for workspaces; contract tests for Connect; AI eval harness for citations.

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
