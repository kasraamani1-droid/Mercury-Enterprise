# Mercury AEOS — Engineering Standards

**Parent:** [MERCURY_AEOS_CONSTITUTION.md](MERCURY_AEOS_CONSTITUTION.md) Article III  
**Version:** 1.0 · 2026-08-14

---

## 1. Purpose

These standards define the **minimum engineering quality bar** for every Mercury change. Pull requests that violate them are incomplete.

---

## 2. Mandatory feature checklist

Before marking a feature done, verify:

| # | Requirement | Evidence |
|---|-------------|----------|
| E1 | Reuses platform services | No new identity/RBAC/audit/workflow/notify/search/file engines |
| E2 | No duplicate business logic | Search codebase; extend existing service |
| E3 | RBAC enforced server-side | `require_permissions` / `has_permissions` + tests |
| E4 | Org isolation | `assert_org_access` or equivalent on queries/mutations |
| E5 | Audit coverage | Mutating privileged paths call audit facade |
| E6 | Event publishing | Domain-significant transitions publish (Framework and/or Fabric) |
| E7 | API surface | Versioned REST under `/api/v1/...`; schemas in OpenAPI |
| E8 | Automation ready | Workflow hooks or events enable non-UI automation |
| E9 | Documentation | README/CHANGELOG touch; architecture or ADR if boundary changes |
| E10 | Independently testable | `backend/tests/…` covering happy path + authz failure |

---

## 3. Code organization

| Rule | Standard |
|------|----------|
| Package layout | Prefer `catalog.py` / `models.py` / `schemas.py` / `service.py` / `router.py` for new domains |
| Layering | Router → Service → Repository/ORM; no SQL in routers |
| Shared types | `ActorContext`, pagination helpers from `shared/` |
| Frontend | Vanilla JS modules; UX2 shell + Workspace Engine for object UX |
| Forbidden | React/Vue/Angular/Next introduction without Constitution amendment |

---

## 4. Data & migrations

- UUID primary keys for new enterprise entities where applicable  
- Alembic revision for schema changes (linear chain; single head)  
- Soft-delete policy: follow domain standard; document exceptions (e.g. immutable event store)  
- No destructive migration without explicit approval and backup note  

---

## 5. API engineering

- Consistent error bodies (`detail`, request/correlation IDs)  
- Pagination via shared `PageParams` / clamp helpers on list endpoints  
- Filtering/sorting documented when exposed  
- Idempotent POSTs where operationally required (document)  
- No secrets in responses  

---

## 6. Security engineering

- Fail closed on missing permission or org mismatch  
- Session cookie attributes per `SECURITY.md`  
- No hardcoded production passwords  
- Rate limits respected; do not bypass middleware for convenience  
- XSS: prefer textContent / esc(); avoid unsanitized `innerHTML` for user data  

---

## 7. Events

- Prefer named catalog events over ad-hoc strings  
- Distinguish: in-process Event Framework vs Digital Thread `fabric_events` vs Enterprise Event Fabric  
- Dual-write only per published contract (do not invent a fourth bus)  

---

## 8. AI

- Advisory only unless amended  
- Persist explanations, assumptions, and human review state when decisions are recorded  
- Never auto-transition airworthiness/release without human role  

---

## 9. Testing

| Type | Expectation |
|------|-------------|
| API/contract | Required for new routers |
| Authz | At least one deny + one allow case for sensitive routes |
| Domain | Lifecycle happy path |
| Frontend | Manual checklist for UX shells; automate when Playwright lands |
| Performance | Required before claiming scale; not optional for GA claims |

---

## 10. Definition of Done

A change is done when E1–E10 are satisfied, docs updated, and existing tests still pass. “Works on my machine” is not Done.
