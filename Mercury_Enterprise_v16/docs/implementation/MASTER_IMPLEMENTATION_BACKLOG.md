# Mercury AEOS — Master Implementation Backlog

| Field | Value |
|-------|-------|
| **Document** | Master Implementation Backlog (Task — Productization Audit) |
| **Date** | 2026-08-14 |
| **Scope** | Complete engineering audit → prioritized epics for **Platform 1.0 RC** |
| **Constraint** | No new enterprise modules or major architectural inventions |
| **Stack truth** | FastAPI modular monolith + **vanilla JS** frontend (not React) |
| **Evidence base** | Codebase audit: 34 packages, Alembic head `20260814_0022`, 463+ tests, UX2 + Workspace Engine |

---

## 1. Executive verdict

Mercury is a **broad, real AEOS foundation** with strong domain APIs (fleet, MRO, planning, logistics, marketplace, twin, network, plugins, event fabric) and a new UX shell. It is **not yet RC-ready** for multi-worker production or customer pilot without finishing hardening, closing frontend↔API gaps on the pilot path, and proving security/tenant isolation under automation.

**Recommended RC posture:** ship a **production-quality pilot RC** with honest labels for simulated command feeds and deferred payments/OIDC — not a certified ops release.

---

## 2. Audit summary (facts)

### 2.1 Modules (backend)

34 packages under `backend/app/`, including: `platform`, `org`, `fleet`, `components`, `maintenance`, `planning`, `work_orders`, `logistics`, `marketplace`, `twin`, `network`, `plugins`, `event_fabric`, `fabric`, `connect`, `ecosystem`, `authority`, `oem`, `personnel`, `publications`, `ai`, …

| Gap | Evidence |
|-----|----------|
| Empty package | Approvals APIs remain in `main.py`; durable SQL table `approval_requests` (RC1 Blocker 03) |
| Thin readiness domains | `authority`, `oem`, `ai` — list/seed oriented |
| Stub-heavy | Maintenance AI index/embedding stubs; `publications/storage.py` abstract `NotImplementedError` |
| Simulated APIs | `main.py` integrations/compliance-style payloads still mark `simulated: True` in places |
| Dual event stacks | Event Framework + Event Fabric + Digital Thread `fabric_events` — dual-write incomplete |

### 2.2 Frontend ↔ API

| Connected to real APIs | Partial / hub only | Simulated / static (labeled) |
|------------------------|--------------------|------------------------------|
| Home KPIs, aircraft CRUD register + list, fleet, WO create/list, marketplace products/cart/quotes, twin list + WE history/config/reliability, orgs, authority, planning, logistics inventory balances, MRO, incidents, decisions, audit, history reports, developer catalogs/installs/subscriptions/DLQ, logbook, engineering AD/SB/EO, approvals inbox, tech library, OEM manufacturers | AI workspace (advisory shell), Admin demo chrome, WE persona types | Command tracks, radar, airport twin HUD, cloud/compliance demos (SIM badges) |

**Deferred full UIs** (API exists): Network, Ecosystem, Connect deep UI, Fabric (non–event-fabric) management, Plugins install/manage write UX.

**Note on “React”:** There is **no React**. Audit item 9 is fulfilled as **vanilla JS / UX2 / Workspace Engine quality**.

### 2.3 CRUD

- **Strongest:** MRO (packages, assign, transitions, inspect, release), incidents (create/resolve), logistics scan  
- **List-open only:** Aircraft, fleet, marketplace, twin, org, authority, developer catalogs  
- **Missing UI CRUD:** Marketplace cart/quote/order, twin history write, planning program forms, most logistics create forms, network/plugins management  

### 2.4 Migrations

- **20** Alembic revisions; **single head `20260814_0020`** (Event Fabric)  
- Linear chain healthy  
- Soft-delete columns exist on newer domains but **few runtime delete paths**; core aviation domains often lack `deleted_at`

### 2.5 Auth / RBAC / tenancy

- Domain routers use `require_session` + `has_permissions` (not only `main.py`)  
- Hardening tests cover former anonymous incident/ops gaps  
- `assert_org_access` / org resolve: strong on logistics/MRO/fleet/planning; **absent** on global catalogs (`authority`, `oem`) by design; risk on legacy command paths  
- **In-memory `_sessions`** — blocks multi-worker HA  
- **`MERCURY_API_KEY` reserved, not enforced**

### 2.6 OpenAPI / API consistency

- FastAPI auto-OpenAPI present  
- Pagination helpers exist (`shared.PageParams`) but **uneven adoption** on legacy lists  
- Filter/sort contracts not uniform  

### 2.7 Tests

- **34** files / **463** collected tests  
- Gaps: tenant-isolation matrix, performance, frontend E2E, Event Fabric dual-write, marketplace checkout UI paths  

### 2.8 Performance

- Large services (`logistics` ~3.5k LOC)  
- Unbounded/legacy list risk  
- No Redis session/cache tier in Compose  
- No formal k6/locust baselines  

### 2.9 Deploy / CI

- Dockerfiles + `docker-compose.yml` / `.env.example` present  
- **No `.github/workflows` inside this package tree** (CI may live only at outer git root — must be verified/fixed for RC)  
- No Redis service in Compose  

---

## 3. Epic backlog

Completion % = engineering judgment from audit (API + UI + tests + ops), not a promise calendar.

---

### EPIC-001 — Platform Hardening

| | |
|--|--|
| **Completion** | **88%** |
| **Complexity** | High |
| **Dependencies** | None (start here with Security) |
| **Dependencies outbound** | Unblocks EPIC-008, EPIC-012 |
| **Status** | **Implemented 2026-08-14** (see `docs/engineering/EPIC001_PLATFORM_HARDENING.md`) |
| **Risk** | **Medium** — remaining list caps + live Redis CI are non-blocking for single-worker pilot |

**Completed tasks**

1. Redis sessions + Compose Redis (EPIC-009) + fail-closed startup/`/ready` when `REDIS_REQUIRED=true`  
2. Event dual-write (Framework → Fabric for `BUS_TO_CATALOG`) + ownership matrix + ADR-0017 note  
3. Pagination caps on fleet/org/personnel/publications/planning/approvals/incidents via `clamp_page` / `Query(le=500)`  
4. Soft-delete policy documented (`SOFT_DELETE_POLICY.md`) — selective; no mass column drop  
5. CI discoverability — `docs/engineering/CI.md`; workflow at parent git root; nested JS syntax check  
6. Health/ready Redis fail-closed verified by tests  
7. Empty `approvals/` shell removed; list API capped in `main.py`  
8. Local disk file object store + `POST /api/v1/platform/files/upload`  

**Acceptance criteria**

- [x] Multi-worker uvicorn with Redis sessions keeps login (Compose Redis + session store; memory fallback documented)  
- [x] CI runs pytest on PR for this repo layout (parent `.github/workflows/ci.yml`)  
- [x] Written event ownership matrix (Framework vs Fabric vs Thread)  
- [x] All RC-critical `/api/v1` list endpoints bounded (fleet/org/personnel/publications/planning/approvals/incidents + Programs 13–17 already capped)  

**Discovered / remaining under EPIC-001 only**

1. Cap remaining nested logistics/components/marketplace cart-style lists — **Medium**  
2. Live Redis integration job in CI — **Medium**  
3. Soft-delete write APIs for marketplace/network/plugins (columns filter-only today) — **Low**  
4. Optional: extract approvals routes from `main.py` into a package — **Low** (SQL persistence done — RC1 Blocker 03)  

---

### EPIC-002 — Frontend Completion

| | |
|--|--|
| **Completion** | **82%** |
| **Complexity** | High |
| **Dependencies** | EPIC-003 for any missing APIs on pilot path |
| **Status** | **Implemented 2026-08-14** (see `docs/engineering/EPIC002_FRONTEND_COMPLETION.md`) |
| **Note** | Vanilla JS only — complete UX2 + Workspace Engine, do not introduce React |
| **Risk** | **Low–Medium** — pilot path API-backed; SIM surfaces remain labeled; E2E automation pending |

**Completed tasks**

1. Aircraft/fleet list + aircraft create form bound to `/fleet`  
2. Work Orders UX2 board: create package/order + open WE session  
3. Marketplace: product detail (WE), cart, quote UI (payments out of scope)  
4. Twin WE tabs wired to history/configuration/reliability/relationships APIs  
5. Digital Logbook: tech-log from `/maintenance/logbook`  
6. Engineering workspace: real AD/SB/EO from planning APIs  
7. Approvals inbox UI for `/approvals`  
8. Developer portal: Event Fabric subscriptions/DLQ read-only; plugin installations  
9. Simulated Command/Radar/Cloud/Ops Twin labeled in nav + page chrome  
10. Workspace Engine: real `createWo` / `openTwin` (create if missing) on aircraft; cart/quote on listings  
11. Technical Library + thin OEM manufacturer catalog (full OEM portal still deferred)

**Acceptance criteria**

- [x] Every **RC pilot screen** loads data from API or shows explicit empty/error (no silent mock as “live”)  
- [x] Aircraft → Workspace Engine → WO/Twin tabs use real related bundles  
- [x] No React / SPA framework introduced  

**Remaining under EPIC-002 only**

1. Registration `make_current` / status detail drawer polish — **Low**  
2. Explicit pagination controls (beyond `limit`) on large lists — **Low**  
3. Network / Ecosystem / Connect full UIs — **Deferred post-RC**  
4. Frontend E2E automation — **Medium** (separate test epic preferred)  
---

### EPIC-003 — Backend Completion

| | |
|--|--|
| **Completion** | **90%** |
| **Complexity** | Medium–High |
| **Dependencies** | EPIC-001 pagination/event policy preferred |
| **Status** | **Implemented 2026-08-14** (see `docs/engineering/EPIC003_BACKEND_COMPLETION.md`) |
| **Risk** | **Low–Medium** — pilot CRUD/authz complete; optional revoke API remains |

**Completed tasks**

1. Aircraft registration GET/PATCH write paths; marketplace cart/quote/order org-scope tests  
2. Temporary access / custom roles merged into runtime via `runtime_authz` + `PermissionService`  
3. Logistics purchase order status machine on `WorkflowBridge` (create/receive/close)  
4. Publications `local_filesystem` storage backend for pilot locators  
5. Dead `approvals/` package already absent (confirmed)  
6. OpenAPI tag descriptions for Programs 13–17  

**Acceptance criteria**

- [x] Pilot entity matrix (Aircraft, WO, Twin, Marketplace product/cart/quote, Org context) has API create/read/update as required by UI  
- [x] Custom role / temp access reflected in authz tests  
- [x] OpenAPI lists all `/api/v1` domain routers (tags + descriptions for RC domains)  

**Discovered / remaining under EPIC-003 only**

1. Optional HTTP revoke for temporary-access grants (DB revoke in tests today) — **Low**  
2. Registration `make_current` UI wiring still thin (list/create done in EPIC-002) — **Low**  

---

### EPIC-004 — Digital Twin Completion

| | |
|--|--|
| **Completion** | **60%** |
| **Complexity** | Medium |
| **Dependencies** | EPIC-002 twin UI; Event Fabric dual-write from EPIC-001 |

**Remaining tasks**

1. Auto-link twin to fleet aircraft / components on create (additive service hooks)  
2. UI: history + configuration + relationships panels (APIs exist)  
3. Publish twin lifecycle events to Event Fabric  
4. Keep **non-3D** positioning; retire confusing “Switch to 3D” airport sim copy or relabel as Ops Twin sim  
5. Reliability remains architecture-only unless product asks otherwise — do not fake ML  

**Acceptance criteria**

- [ ] Open aircraft → Digital Twin tab shows linked twin or “create twin” action  
- [ ] Twin history visible in UI from API  
- [ ] Disclaimer “not a 3D model” retained  

---

### EPIC-005 — Marketplace Completion

| | |
|--|--|
| **Completion** | **55%** |
| **Complexity** | Medium |
| **Dependencies** | EPIC-002 marketplace UI |

**Remaining tasks**

1. Frontend: cart, quote request, order list (backend routes exist)  
2. Org-scoped permission tests for buyer/seller flows  
3. Keep `payment_status=not_configured` — **no payment rails in RC**  
4. Seller onboarding minimal UI or admin seed path documented  
5. Search/favorites if APIs exist — wire or defer explicitly  

**Acceptance criteria**

- [ ] Demo buyer can add to cart and request quote via UI  
- [ ] Payments clearly disabled  
- [ ] Tenant isolation tests for marketplace writes  

---

### EPIC-006 — AI Integration

| | |
|--|--|
| **Completion** | **25%** |
| **Complexity** | High (if real LLM); Low (if RC-scoped) |
| **Dependencies** | Search metadata; security review |
| **RC recommendation** | **Minimal** — do not block RC on LLM vendor |

**Remaining tasks (RC-minimal)**

1. Keep advisory-only labels on Copilot + WE AI  
2. Replace WE AI template with call to existing `/ai` or decisions advisory if present; else keep explicit “rules/demo” badge  
3. Document AI stubs (`AiDocumentIndexStub`) as non-GA  

**Remaining tasks (post-RC)**

4. Optional LLM adapter behind Connect + feature flag  
5. Embedding pipeline workers  

**Acceptance criteria (RC)**

- [ ] No screen implies certified autonomous AI  
- [ ] AI surfaces either call real advisory API or show Demo badge  

---

### EPIC-007 — Mobile Support

| | |
|--|--|
| **Completion** | **15%** |
| **Complexity** | High |
| **Dependencies** | EPIC-002 MRO/hangar flows |
| **RC recommendation** | **Defer full mobile app**; ship responsive hangar CSS + offline queue polish only |

**Remaining tasks (RC-minimal)**

1. Responsive pass on MRO + logistics scan + Workspace Engine rail  
2. Offline queue visibility/status already in MRO — harden empty/error states  

**Post-RC**

3. PWA / native hangar client  

**Acceptance criteria (RC)**

- [ ] MRO + scan usable at 390px width  
- [ ] No claim of native mobile app in RC notes  

---

### EPIC-008 — Performance

| | |
|--|--|
| **Completion** | **30%** |
| **Complexity** | Medium |
| **Dependencies** | EPIC-001 pagination + Redis |

**Remaining tasks**

1. Index audit on hot tables (org_id, status, aircraft_id, created_at)  
2. k6/locust smoke: login, list aircraft, list WO, dashboard  
3. N+1 review on logistics/planning heavy list endpoints  
4. Optional Redis cache for permission matrix / session only (no new product cache layer)  

**Acceptance criteria**

- [ ] Documented p95 for 3 smoke scenarios on Compose  
- [ ] No unbounded list endpoints on RC path  

---

### EPIC-009 — Security

| | |
|--|--|
| **Completion** | **92%** |
| **Complexity** | High |
| **Dependencies** | None — **start immediately** |
| **Status** | **Implemented 2026-08-14** (see `docs/security/EPIC009_RC_NOTES.md`) |

**Completed tasks**

1. Redis sessions — `security/sessions.py`; Compose `redis` service; memory fallback  
2. Automated tenant-isolation suite — `tests/test_epic009_security.py` (fleet, WO, marketplace, twin, logistics, planning, context)  
3. `MERCURY_API_KEY` enforced when set — `security/api_key.py` + `require_session`  
4. Cookie Secure defaults verified (production startup refuse + regression test)  
5. XSS sweep — command palette labels escaped; existing esc() paths confirmed on org selectors / incidents  
6. OIDC/SSO deferred with explicit RC exclusion documented  

**Acceptance criteria**

- [x] Tenant isolation tests green for RC domains  
- [x] Production compose rejects insecure demo password defaults (startup validation + test)  
- [x] Security section in RC notes lists deferred SSO/MFA  

**Discovered / remaining under EPIC-009 only**

1. Optional: integration test against live Redis container in CI (unit covers memory backend; Redis path needs Compose job) — **Low**  
2. Optional: rotate API-key via admin without restart — **Deferred** (env-based key is intentional for RC)  
3. Broader XSS pass on legacy `maintenance.js` / `planning.js` dynamic hosts — **Medium follow-up** (most paths already `esc()`; not blocking EPIC-009 AC)  
---

### EPIC-010 — Documentation

| | |
|--|--|
| **Completion** | **75%** |
| **Complexity** | Low–Medium |
| **Dependencies** | Parallel; finalize before EPIC-012 |

**Remaining tasks**

1. Consolidate duplicate ADR-0001–0006 numbering  
2. Single **RC Runbook**: deploy, seed, demo script, known simulated surfaces  
3. OpenAPI publish step in CI or static export in docs  
4. Align IMPLEMENTATION_STATUS / FINAL_RELEASE_GATE with current fixes  
5. Constitution PR checklist reference  

**Acceptance criteria**

- [ ] New engineer can deploy Compose pilot from one runbook  
- [ ] ADR index unique  
- [ ] Simulated vs live matrix published  

---

### EPIC-011 — Demo Environment

| | |
|--|--|
| **Completion** | **50%** |
| **Complexity** | Medium |
| **Dependencies** | EPIC-002, EPIC-003, EPIC-005 |

**Remaining tasks**

1. One-command demo seed: org, aircraft C-GMEA, twin link, WO, marketplace products, plugin catalog  
2. Demo persona logins (Technician / Planner / Admin) with RBAC  
3. Scripted click-path doc: Home → Aircraft → Twin → WO → Marketplace quote  
4. Separate **Command sim profile** so ops demo does not pollute MRO pilot narrative  
5. Reset script for shared demo tenants  

**Acceptance criteria**

- [ ] Fresh Compose up + seed → demo path works without manual SQL  
- [ ] Labels distinguish Command simulation vs AEOS pilot data  

---

### EPIC-012 — Release Candidate (RC1)

| | |
|--|--|
| **Completion** | **35%** |
| **Complexity** | Medium (integration) |
| **Dependencies** | EPIC-001, 002, 003, 009, 010, 011; 004/005/008 minimal bars |

**Remaining tasks**

1. Freeze scope: AEOS pilot = Org + Fleet/Aircraft + Planning/MRO + Logistics scan + Twin + Marketplace quote + Platform auth  
2. Tag `v1.0.0-rc.1` only after gates below  
3. RC evidence pack: pytest, tenant tests, Compose smoke, security notes  
4. Explicit **Non-goals** in release notes: payments, OIDC, Network UI, native mobile, certified AI, Kafka broker  
5. Rollback / DR pointer from existing runbooks  

**Acceptance criteria**

- [ ] All RC acceptance criteria in EPIC-001/002/003/009/011 met  
- [ ] 463+ tests green (or successor count) in CI  
- [ ] Constitution Article V fabric integrations satisfied for **in-scope** products  
- [ ] No “GA / certified” wording in RC artifacts  

---

## 4. Recommended epic order (to Platform 1.0 RC)

Execute in this sequence (parallelization noted):

| Order | Epic | Why |
|------:|------|-----|
| **1** | **EPIC-009 Security** | Tenant + sessions are hard blockers for any pilot |
| **2** | **EPIC-001 Platform Hardening** | Redis/CI/pagination/events — foundation for scale claims |
| **3** | **EPIC-003 Backend Completion** | Close only pilot CRUD/authz holes |
| **4** | **EPIC-002 Frontend Completion** | Connect pilot screens to real APIs; WE depth |
| **5** | **EPIC-011 Demo Environment** | Reproducible pilot path |
| **6** | **EPIC-005 Marketplace Completion** *(RC-minimal)* | Cart/quote UI — no payments |
| **7** | **EPIC-004 Digital Twin Completion** *(RC-minimal)* | Link + history UI |
| **8** | **EPIC-008 Performance** | Baselines before RC tag |
| **9** | **EPIC-010 Documentation** | Runbook + ADR cleanup |
| **10** | **EPIC-012 Release Candidate (RC1)** | Freeze, evidence, tag |
| **Defer** | **EPIC-006 AI** (beyond labels) | Post-RC |
| **Defer** | **EPIC-007 Mobile** (beyond responsive) | Post-RC |

```
009 ──┬── 001 ── 003 ── 002 ── 011 ──┬── 005 ──┐
      │                              └── 004 ──┼── 008 ── 010 ── 012
      └────────────────────────────────────────┘
         (006, 007 after RC1)
```

---

## 5. Out of scope for this backlog (intentional)

- New analytics gateway / dedicated API gateway service / Kafka  
- React/Vue migration  
- Payment processors  
- Certified airworthiness automation  
- Full Aviation Network product UI (unless pulled into a later RC)  
- Live OEM SDK embeds without Connect vault  

---

## 6. Traceability

| Audit question | Primary epic(s) |
|----------------|-----------------|
| Incomplete / TODO / stubs | 001, 003, 006 |
| Frontend ↔ API | 002, 011 |
| Missing CRUD | 002, 003, 005 |
| Migrations | 001 (policy), healthy head today |
| Authn/z on endpoints | 009, 003 |
| Tenant isolation | 009 |
| OpenAPI consistency | 001, 003, 010 |
| “React” / UI quality | 002 (vanilla JS) |
| Tests | 009, 008, 012 |
| Performance | 008 |
| Docker / CI / prod | 001, 010, 012 |

---

**Document owner:** CTO / Principal Engineer  
**Next action:** Proceed to **EPIC-011 Demo Environment** (or EPIC-005/004 RC-minimal polish as needed). EPIC-002 frontend completion is at **82%**; EPIC-003 at **90%**; EPIC-001 at **88%**; EPIC-009 at **92%**.
