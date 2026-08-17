# Naming Standards

| Field | Value |
|-------|--------|
| Document | Naming Standards |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Naming Standards for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
Consistency across APIs, database, permissions, UI, and ADRs so the Digital Thread is searchable by humans and machines.

## 3. Normative requirements
| Area | Rule | Example |
|------|------|---------|
| API paths | kebab-case under `/api/v1` | `/logistics/material-requests` |
| JSON fields | snake_case | `organization_id` |
| DB tables | snake_case plural domain prefix where needed | `logistics_stock_movements` |
| Permissions | `domain.action` | `work_order.execute` |
| Python packages | snake_case modules | `backend/app/logistics` |
| JS modules | camelCase files matching workspace | `logistics.js` |
| ADR files | `ADR-NNNN-slug.md` | `ADR-0008-ai-advisory-only.md` |
| Org IDs | opaque string ids | `org-aviation-east` |
| Part numbers | uppercase normalized on write | `MS21042L3` |

## 4. NFRs / Security / Scalability
Stable names are API contracts — renames require versioning. Permission names are security-critical; do not reuse retired codes.

## 5. Future
Public registry of permission codes in Developer Platform.

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
