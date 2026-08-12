# Mercury Enterprise V2.0 — Final Release Verification

| Field | Value |
|-------|--------|
| **Date** | 2026-08-10 |
| **Branch** | `task-16-audit-provenance` (ahead of origin by 4 commits + large uncommitted hardening/docs delta) |
| **Package** | `Mercury_Enterprise_v16/` |
| **Mode** | Verification only — **no production code changes, no tag, no merge, no commit** |
| **Prior decision** | `RC2_FINAL_ACTION_PLAN.md` → READY FOR RELEASE (engineering) pending High validation |

---

## Summary matrix

| # | Check | Result |
|---|--------|--------|
| 1 | Working tree is clean | **FAIL** |
| 2 | No temporary files | **FAIL** |
| 3 | No SQLite artifacts | **FAIL** |
| 4 | No demo credentials remain | **FAIL** |
| 5 | CI passes | **FAIL** |
| 6 | Backend tests pass | **PASS** |
| 7 | Frontend tests pass | **PASS** (syntax suite) |
| 8 | Docker build succeeds | **FAIL** |
| 9 | Compose starts successfully | **FAIL** |
| 10 | Release notes are current | **FAIL** |
| 11 | Version numbers are consistent | **FAIL** |
| 12 | Git ignore contains runtime artifacts | **PASS** (with caveat) |

```text
OVERALL: NO GO
```

---

## 1. Working tree is clean — FAIL

**Evidence:** `git status` shows **52** porcelain lines: many modified hardening/docs files, deleted nested CI / tmp stubs, modified `mercury.db`, and untracked Alembic, design docs, root `.github/`, `RELEASE_NOTES_v2.0.md`, etc.

**Impact:** Cannot tag a reproducible release from a dirty tree; tag would omit or partially include hardening work.

**Release blocker:** **Yes**

---

## 2. No temporary files — FAIL

**Evidence:**
- On-disk `tmp_models.txt` / `tmp_schemas.txt` are marked deleted in the working tree (`D`) but **still exist in the last committed tree** (`git ls-files` lists them).
- Cleanup is incomplete until a commit removes them from history’s tip.

**Impact:** Temporary design dumps remain part of the committed package until committed deletion lands.

**Release blocker:** **Yes** (until committed removal or confirmed absent from release tree)

---

## 3. No SQLite artifacts — FAIL

**Evidence:**
- Tracked: `Mercury_Enterprise_v16/mercury.db`, `Mercury_Enterprise_v16/backend/mercury.db` (`git ls-files`)
- Working tree: `mercury.db` modified (`M`)
- Also present on disk: `mercury_task16_test.db`
- `.gitignore` includes `*.db` / `*.sqlite3`, but **already-tracked** DBs are not ignored

**Impact:** Runtime database blobs can ship inside a tag; non-reproducible and environment-specific.

**Release blocker:** **Yes**

---

## 4. No demo credentials remain — FAIL

**Evidence (intentional dev leftovers, still present in tree):**
- `backend/app/core/config.py` — development default password `mercury-demo` when `MERCURY_ENV` is not production
- `frontend/js/app.js` — still contains `password: "mercury-demo"` behind `__MERCURY_DEMO_AUTO_LOGIN__`
- Backend tests hardcode `mercury-demo` (acceptable for tests; still “demo credentials in tree”)
- Docs/README still document the demo password for local use

**Mitigations already present (do not clear this FAIL against the checklist wording):**
- Production startup refuses missing/short/`mercury-demo` passwords
- Default UI path requires interactive login (auto-login off unless flag)

**Impact:** Checklist item “no demo credentials remain” is not satisfied for a strict production release cut.

**Release blocker:** **Yes** for this verification standard (narrow: remove/default-empty outside tests + require env always; or waive in writing)

---

## 5. CI passes — FAIL

**Evidence:**
- Git-root workflow **exists**: `.github/workflows/ci.yml` (**untracked**)
- Nested package workflow deleted in working tree (uncommitted)
- `gh` CLI **not available**; no Actions run observed on this host
- Cannot claim CI green without a remote workflow execution

**Local CI-equivalent (informative only):** pytest 80 passed; compileall PASS; node --check PASS — **not** a substitute for “CI passes”

**Release blocker:** **Yes**

---

## 6. Backend tests pass — PASS

**Evidence:** `PYTHONPATH=backend pytest -q backend/tests` → **80 passed**, 128 warnings (`utcnow` deprecation only).

**Release blocker:** No

---

## 7. Frontend tests pass — PASS

**Evidence:** No dedicated frontend unit-test framework in repo. Applied available suite: `node --check` on all `frontend/js/*.js` → **PASS**.

**Release blocker:** No (within available test surface)

---

## 8. Docker build succeeds — FAIL

**Evidence:** Docker CLI **not installed / not on PATH** on the verification host (`docker` command missing).

**Release blocker:** **Yes** (cannot verify images)

---

## 9. Compose starts successfully — FAIL

**Evidence:** Same as §8 — Compose cannot be executed here. Matches prior `H-VAL-1` gap in `RC2_FINAL_ACTION_PLAN.md`.

**Release blocker:** **Yes**

---

## 10. Release notes are current — FAIL

**Evidence:** `docs/RELEASE_NOTES_v2.0.md` still describes **pre-hardening** state:
- Validation cited as **70/70** (now 80)
- Known limitations still list hardcoded WS `:8000` and open packaging checklist items that hardening already fixed
- Status still “awaiting approval” / merge not updated for READY FOR RELEASE + hardening completion
- Hardening / Alembic / workers=1 / interactive login not reflected as completed

**Release blocker:** **Yes**

---

## 11. Version numbers are consistent — FAIL

**Evidence:**
| Location | Label |
|----------|--------|
| `MERCURY_VERSION` / API tests | `16.0.0` |
| UI `index.html` | `v16.0` |
| Product docs / APPLY_TASK | V2.0 |
| `START_ALL.bat` | v15.0 / v10 window titles |
| `START_BACKEND.bat` | v10 |
| `CHECK_SYSTEM.bat` | v15.0 |
| README title | v16.0 |

**Impact:** Operator confusion; release identity unclear (V2.0 vs 16.0.0 vs legacy v10/v15).

**Release blocker:** **Yes** for consistency gate (cosmetic but explicit checklist item)

---

## 12. Git ignore contains runtime artifacts — PASS (caveat)

**Evidence:** `Mercury_Enterprise_v16/.gitignore` includes:
- `__pycache__/`, `*.py[cod]`
- `.venv/`, `.pytest_cache/`
- `*.db`, `*.sqlite3`
- `.env`, `.env.*` with `!.env.example`
- `frontend/js/config.local.js`
- OS junk

**Caveat:** Tracked SQLite files (§3) bypass ignore until `git rm --cached`. Ignore rules themselves are adequate.

**Release blocker:** No for ignore content; **Yes** indirectly via §3 until DBs untracked

---

## Release blockers (aggregated)

1. Dirty working tree (uncommitted hardening + docs)  
2. Temporary files still in committed tip / pending delete incomplete  
3. Tracked / present SQLite database artifacts  
4. Demo credentials still present in non-test production-facing code paths (dev default + optional auto-login string)  
5. CI not proven green (no Actions run; root workflow untracked)  
6. Docker build not verified  
7. Compose start not verified  
8. Release notes stale vs hardening  
9. Version string drift (v10/v15/v16/V2.0)

**Non-blockers for this verification:** Backend pytest; frontend syntax checks; `.gitignore` pattern set.

---

## Release recommendation

```text
NO GO
```

Do **not** tag. Do **not** merge. Do **not** commit from this verification step.

### Minimum to re-attempt `GO TO TAG`

1. Commit (or explicitly stage) the full hardening + docs set on a clean reviewable tip — **separate explicit commit approval**  
2. `git rm --cached` SQLite DBs; ensure no `*.db` in tree; confirm tmp files gone from tip  
3. Refresh `docs/RELEASE_NOTES_v2.0.md` for hardening + 80 tests + READY FOR RELEASE  
4. Align launcher/UI version banners to `16.0.0` / V2.0 policy  
5. Decide demo-credential policy for the tagged artifact (strip defaults outside tests **or** documented waiver)  
6. On a Docker host: `docker compose build` + `up` smoke; record evidence  
7. Push so git-root CI runs green (or record equivalent CI proof)  
8. Re-run this verification checklist → expect all **PASS** → then **GO TO TAG**

### Explicit non-actions performed

- No production code modified  
- No tag  
- No merge  
- No commit  

---

**Signed verification outcome: NO GO**
)
