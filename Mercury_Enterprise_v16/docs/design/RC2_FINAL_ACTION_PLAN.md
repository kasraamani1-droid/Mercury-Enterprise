# Mercury Enterprise V2.0 — RC2 Final Action Plan

| Field | Value |
|-------|--------|
| **Date** | 2026-08-10 |
| **Inputs** | `docs/design/PRODUCTION_HARDENING_REPORT.md`, `FINAL_RELEASE_GATE.md`, `PRODUCTION_HARDENING_SPEC.md`, current tree |
| **Mode** | Review only — **no code, merge, tag, or commit** |
| **Prior hardening** | Critical/High gate IDs C1–C8 / H1–H7 implemented; tests **80 passed** |

---

## Verdict snapshot

| Question | Answer |
|----------|--------|
| Critical blockers remaining? | **None** |
| Stop for Critical implementation? | **No** (none to implement) |
| Release recommendation | **READY FOR RELEASE** (engineering V2.0 hardened pilot) **after** High validation checklist below — **not** a new feature RC2 |
| Certified / safety-critical / internet multi-tenant ops | Still **out of scope** (Future) — do not market as certified |

```text
CRITICAL COUNT: 0
RECOMMENDATION: READY FOR RELEASE
(with High pre-tag validation; no RC2 feature cycle required)
```

---

## Closed by production hardening (context)

These were Critical/High at gate and are **not** remaining blockers:

C1–C4 packaging, C5–C8 identity/authz, H1 open reads, H2 CI path, H3 Alembic baseline, H4 Secure cookie default, H5 XSS (commandCenter/liveOps), H6 list caps, H7 `.env.example`.

---

## Remaining items by severity

### Critical (must fix)

**None.**

No open Critical code or configuration defects were found after hardening. Original Critical IDs are remediated in-tree.

---

### High

#### H-VAL-1 — Compose / NGINX runtime not proven on a Docker host

| Field | Detail |
|-------|--------|
| **Root cause** | Hardening host lacked Docker CLI; packaging fixes were unit/smoke tested via TestClient and static checks only |
| **Impact** | Risk of undiscovered proxy/cookie/WS/env issues at first real Compose deploy; CONDITIONAL GO cannot become unconditional without evidence |
| **Files** | `docker-compose.yml`, `frontend/nginx.conf`, `.env.example`, frontend `config.js` / `websocket.js` (verify only) |
| **Required implementation** | **Validation only** (no feature code): `docker compose up --build`; hit `http://localhost:3000/api/v1/ready`; interactive login; dashboard; WS; decision evaluate; confirm host `:8000` unused |
| **Estimated effort** | 0.5–1 day (environment + smoke + note in gate) |
| **Blocks production?** | **Yes for tagging a production/pilot deploy** until smoke passes. Does **not** require RC2 feature work if smoke passes |

#### H-IDOR-1 — Incident write paths not site-scoped

| Field | Detail |
|-------|--------|
| **Root cause** | Hardening scoped **GET** incidents via `_get_scoped_incident`; `PATCH .../status`, `POST .../events`, `POST .../evidence` still use unscoped `db.get(Incident)` |
| **Impact** | Authenticated operator who learns another site’s incident UUID could mutate it (multi-tenant integrity risk) |
| **Files** | `backend/app/main.py` (`update_incident_status`, `add_event`, `add_evidence`); tests under `backend/tests/` |
| **Required implementation** | Reuse `_get_scoped_incident` (or equivalent) on those write routes; add cross-site negative tests |
| **Estimated effort** | 0.5 day |
| **Blocks production?** | **Yes for multi-site production**. **No** for single-site controlled pilot if org/site cannot be switched across tenants by attackers. Recommend fix before broad multi-tenant deploy; optional before single-site pilot tag |

#### H-XSS-1 — Residual `innerHTML` sinks outside hardened modules

| Field | Detail |
|-------|--------|
| **Root cause** | Spec fixed `commandCenter.js` / `liveOps.js`; other modules still build HTML (some escaped, some static catalogs) |
| **Impact** | Lower than pre-hardening; residual risk if server/user strings reach unescaped sinks (e.g. decision factor text, enterprise static demos) |
| **Files** | `frontend/js/app.js` (decision panels — partially escaped), `enterprise.js`, `enterprise8.js`, `incidents.js` (mostly escaped), `copilot.js` |
| **Required implementation** | Audit all `innerHTML` assignments; apply existing `esc()` consistently; prefer `textContent` where possible |
| **Estimated effort** | 1–2 days |
| **Blocks production?** | **Yes for hostile multi-operator / untrusted content**. **Borderline** for closed demo with trusted operators — treat as High pre-internet |

#### H-CI-1 — CI discoverable but live Actions run not evidenced

| Field | Detail |
|-------|--------|
| **Root cause** | Workflow moved to git root; no merge/push performed; Actions green run not observed |
| **Impact** | Automation may still fail on path/Python/Node in Actions environment |
| **Files** | `.github/workflows/ci.yml` |
| **Required implementation** | Push branch or workflow_dispatch (when approved) and confirm green; fix only if CI fails |
| **Estimated effort** | 0.5 day (+ fix time if red) |
| **Blocks production?** | **Yes for release process hygiene** before merge to main; not a product defect until proven red |

---

### Medium

#### M1 — In-memory decisions / approvals / missions / sessions

| Field | Detail |
|-------|--------|
| **Root cause** | Milestone 2 Option A + in-process session dict; workers pinned to 1 |
| **Impact** | State lost on restart; cannot horizontally scale API |
| **Files** | `backend/app/main.py` (`_sessions`, `_approvals`), `decision/`, `missions/` |
| **Required implementation** | Shared session store + durable decision/approval store (follow-on HA spec) |
| **Estimated effort** | 1–2 weeks |
| **Blocks production?** | **No** for single-node pilot with workers=1. **Yes** for HA scale-out |

#### M2 — `MERCURY_API_KEY` reserved but unused

| Field | Detail |
|-------|--------|
| **Root cause** | Config reserved; session RBAC is primary control |
| **Impact** | Docs/ops confusion if operators assume API-key protection |
| **Files** | `backend/app/core/config.py`, `docs/SECURITY.md` |
| **Required implementation** | Either wire optional key middleware or remove from marketing claims (docs already honest) |
| **Estimated effort** | 0.5–2 days |
| **Blocks production?** | **No** if operators follow SECURITY.md |

#### M3 — CORS `allow_headers=["*"]`

| Field | Detail |
|-------|--------|
| **Root cause** | Permissive FastAPI CORS defaults for demo |
| **Impact** | Broader than needed with credentialed cookies |
| **Files** | `backend/app/main.py` CORS middleware |
| **Required implementation** | Restrict to required headers (`Content-Type`, etc.) |
| **Estimated effort** | 0.25 day |
| **Blocks production?** | **No** if `MERCURY_CORS_ORIGINS` is tight |

#### M4 — Simulated feeds / non-certified AI

| Field | Detail |
|-------|--------|
| **Root cause** | Product scope of reference/demo platform |
| **Impact** | Unsuitable for live safety/security decisions |
| **Files** | Domain engines, UI copy, `IMPLEMENTATION_STATUS.md` |
| **Required implementation** | Real adapters + certification program (outside V2.0) |
| **Estimated effort** | Months (program) |
| **Blocks production?** | **Blocks certified ops**. Does **not** block engineering/pilot release of a labeled simulated platform |

#### M5 — (alias of H-VAL-1) Compose validation gap

Tracked above as **H-VAL-1** (elevated from report Medium because it gates tag confidence).

#### M6 — Unbounded in-memory growth (approvals / missions)

| Field | Detail |
|-------|--------|
| **Root cause** | Dict stores without TTL/caps (alerts/decisions already capped) |
| **Impact** | Long-running process memory growth |
| **Files** | `main.py` `_approvals`, `missions/mission_manager.py` |
| **Required implementation** | TTL/max size / eviction |
| **Estimated effort** | 1–2 days |
| **Blocks production?** | **No** for short pilots; **yes** for long-lived unattended |

---

### Future

| ID | Item | Notes | Effort | Blocks V2.0 engineering release? |
|----|------|-------|--------|----------------------------------|
| F1 | OIDC/SSO + MFA | Replace shared password map | Weeks–months | No (pilot); Yes (enterprise IdP mandate) |
| F2 | Redis/shared sessions + multi-worker | After F-session design | 1–2 weeks | No while workers=1 |
| F3 | Durable decision/approval store | Supersede Option A | 1–2 weeks | No for advisory demo |
| F4 | Signed/immutable audit ledger | Compliance product | Weeks | No |
| F5 | Rate limiting / WAF / K8s HA | Ops stack | Weeks | No for single Compose |
| F6 | Load/soak/WS fan-out testing | Performance program | Days–weeks | No for demo scale |
| F7 | Version label cleanup (v10/v15 bats) | Cosmetic | 0.5 day | No |
| F8 | `datetime.utcnow` modernization | Deprecation warnings | 0.5–1 day | No |

---

## Decision tree

```text
Critical remaining? ──No──► Complete High validation (H-VAL-1, H-CI-1)
                              │
                              ├─ Prefer multi-tenant? ──Yes──► Fix H-IDOR-1 before tag
                              │
                              ├─ Internet / untrusted operators? ──Yes──► Fix H-XSS-1 before tag
                              │
                              └─ Single-site closed pilot?
                                   └─► READY FOR RELEASE (V2.0 hardened)
                                         after H-VAL-1 + H-CI-1 green

Certified / live safety ops? ──► Still Future (not V2.0 release criteria)
```

---

## READY FOR RELEASE vs REQUIRES RC2

| Option | Meaning | Applies when |
|--------|---------|--------------|
| **READY FOR RELEASE** | Tag/merge V2.0 as hardened engineering/pilot RC after High **validation** (and optional H-IDOR/H-XSS if threat model requires) | No Critical defects; stakeholders accept simulated-data scope and single-node limits |
| **REQUIRES RC2** | New candidate cycle with substantive feature/hardening beyond validation | Only if High items fail Compose smoke, or product expands to multi-tenant internet / SSO / HA as must-haves for “V2.0 production” |

### Formal recommendation

**READY FOR RELEASE** — Mercury Enterprise **V2.0 hardened engineering release** — subject to:

1. Pass **H-VAL-1** Compose smoke on a Docker host  
2. Confirm **H-CI-1** Actions green  
3. Explicit release notes stating: simulated feeds; single worker; shared-password auth (not SSO); not certified for operational safety  

**Do not open RC2** solely for Medium/Future items (M1–M4, F1–F8).

**Do open a focused patch (or RC2) only if** Compose validation fails, or the approved production threat model requires **H-IDOR-1** / **H-XSS-1** before any external exposure.

---

## Suggested pre-tag checklist (not implementation)

- [ ] `docker compose up --build` + UI/API/WS smoke (H-VAL-1)  
- [ ] CI green on git-root workflow (H-CI-1)  
- [ ] `.env` from `.env.example` with strong password; `MERCURY_ENV=production`  
- [ ] Threat-model decision: single-site pilot vs fix H-IDOR-1 / H-XSS-1 first  
- [ ] Update gate doc from CONDITIONAL GO → GO (pilot) after evidence  
- [ ] Then — and only then — approve tag/merge in a separate explicit request  

---

## Explicit non-actions (this step)

- No code changes  
- No merge  
- No tag  
- No commit  

**Stopped.** Awaiting approval on release path (tag after High validation vs optional IDOR/XSS patch first).
)
