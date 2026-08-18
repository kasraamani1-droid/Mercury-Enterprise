# Multi-Tenant Standards

| Field | Value |
|-------|--------|
| Document | Multi-Tenant Standards |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Multi-Tenant Standards for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
Shared schema, `organization_id` discriminator, **service-layer enforcement** ([ADR-0003](ADR/ADR-0003-multi-tenant-org-isolation.md)).

## 3. Normative requirements
- Every tenant entity carries organization_id.
- Services call assert_org_access before mutate/read of foreign org.
- Memberships define effective role per org.
- Cross-org sharing only via explicit audited constructs (Planned) — never by disabling filters.

## 4. Testing
Mandatory cross-org 403 tests per module.

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
