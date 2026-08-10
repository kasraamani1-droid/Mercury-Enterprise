# Mercury Enterprise V2.0 — Final Commit Audit

| Field | Value |
|-------|--------|
| **Date** | 2026-08-10 |
| **Branch** | `task-16-audit-provenance` |
| **Mode** | Read-only audit of `git status` — **no stage / commit / restore** |
| **Purpose** | Decide what belongs in the release commit vs what to drop or leave ignored |

**Legend**

| Action | Meaning |
|--------|---------|
| **Commit** | Include in the next approved release commit |
| **Restore** | Discard working-tree change (`git restore`); keep last committed version |
| **Ignore** | Do not add; keep out of git (gitignore / leave untracked forever) |

---

## Attention items (requested)

### `.github/workflows/ci.yml` (untracked root) **and** `Mercury_Enterprise_v16/.github/workflows/ci.yml` (deleted)

| | |
|--|--|
| **Why changed** | Production hardening **H2**: GitHub Actions only discovers workflows at the **git root**. Nested `Mercury_Enterprise_v16/.github/workflows/ci.yml` was invisible to Actions. Content was moved/rewritten to root `.github/workflows/ci.yml` (auth env for pytest, full JS `node --check`, optional compose/build). Nested file deleted in the working tree. |
| **Recommendation** | **Commit** root `.github/` (add). **Commit** deletion of nested `Mercury_Enterprise_v16/.github/workflows/ci.yml`. |
| **Do not** | Restore nested CI (would re-break discovery). Ignore root CI (would leave CI broken). |

### `backend/app/security/api_key.py` (deleted)

| | |
|--|--|
| **Why changed** | Final cleanup / release audit: `require_api_key` was **dead code** (never wired to routes). Session RBAC is the real control plane; `MERCURY_API_KEY` remains config-reserved only. File removed to avoid implying API-key middleware exists. |
| **Recommendation** | **Commit** the deletion. |
| **Do not** | Restore unless you intentionally reintroduce unused middleware (not needed for V2.0). |

### `mercury.db` and `backend/mercury.db` (deleted)

| | |
|--|--|
| **Why changed** | Release verification: SQLite runtime DBs were incorrectly **tracked** in git. Removed from disk and shown as deletions so the tip no longer ships environment-specific DB blobs. `.gitignore` already lists `*.db`. |
| **Recommendation** | **Commit** both deletions (untrack + remove from tree). |
| **Do not** | Restore (would put runtime DBs back into the repo). After commit they stay **ignored** if recreated locally. |

### `tmp_models.txt` / `tmp_schemas.txt` (deleted)

| | |
|--|--|
| **Why changed** | Scratch dumps from earlier model/schema exploration; not product artifacts. Removed as temporary-file cleanup; `.gitignore` now has `tmp_*.txt`. |
| **Recommendation** | **Commit** both deletions. |
| **Do not** | Restore or re-add. |

---

## Modified files (` M`)

| Path | Why it changed | Action |
|------|----------------|--------|
| `Mercury_Enterprise_v16/.env.example` | Hardening H7 + credential elimination: template for required `MERCURY_AUTH_PASSWORD`, production flags, no demo default | **Commit** |
| `Mercury_Enterprise_v16/.gitignore` | Ignore runtime DBs, `.env`, `config.local.js`, `tmp_*.txt`, caches | **Commit** |
| `Mercury_Enterprise_v16/CHECK_SYSTEM.bat` | Version sync to V2.0 / 16.0.0; warn if password/`.env` missing | **Commit** |
| `Mercury_Enterprise_v16/IMPLEMENTATION_STATUS.md` | Align identity (V2.0 / 16.0.0) and hardening reality | **Commit** |
| `Mercury_Enterprise_v16/README.md` | Current start/env/version docs; no demo password default | **Commit** |
| `Mercury_Enterprise_v16/START_ALL.bat` | V2.0 labels; require `MERCURY_AUTH_PASSWORD` / load `.env` | **Commit** |
| `Mercury_Enterprise_v16/START_BACKEND.bat` | Same; load `.env`; fail if password unset | **Commit** |
| `Mercury_Enterprise_v16/START_DOCKER.bat` | Do not auto-copy empty `.env`; require password in `.env` | **Commit** |
| `Mercury_Enterprise_v16/START_FRONTEND.bat` | V2.0 title; create `config.local.js` for dual-process local API | **Commit** |
| `Mercury_Enterprise_v16/backend/Dockerfile` | C4: `--workers 1` for in-memory sessions | **Commit** |
| `Mercury_Enterprise_v16/backend/app/core/config.py` | Require env password; forbid demo defaults; Secure cookie by env | **Commit** |
| `Mercury_Enterprise_v16/backend/app/database.py` | Document Alembic vs `create_all` | **Commit** |
| `Mercury_Enterprise_v16/backend/app/main.py` | Hardening: scoped/auth’d incident GETs, alerts/dashboard/platform, pagination, counts, startup password validation | **Commit** |
| `Mercury_Enterprise_v16/backend/app/ops/service.py` | Cleanup: share orchestrator singleton (no second instance) | **Commit** |
| `Mercury_Enterprise_v16/backend/app/routers/connectors.py` | Cleanup: unused import removal | **Commit** |
| `Mercury_Enterprise_v16/backend/app/routers/ops.py` | C6/H1: auth on ops health/coordinate + audit | **Commit** |
| `Mercury_Enterprise_v16/backend/app/security/authorization.py` | New permissions: `incident.read`, `alerts.read`, `dashboard.read`, `platform.read`, `ops.*` | **Commit** |
| `Mercury_Enterprise_v16/backend/requirements.txt` | Add `alembic` | **Commit** |
| `Mercury_Enterprise_v16/backend/tests/conftest.py` | Set test-only `MERCURY_AUTH_PASSWORD` before app import | **Commit** |
| `Mercury_Enterprise_v16/backend/tests/test_api.py` | Auth expectations + `TEST_AUTH_PASSWORD` | **Commit** |
| `Mercury_Enterprise_v16/backend/tests/test_audit.py` | Same | **Commit** |
| `Mercury_Enterprise_v16/backend/tests/test_connectors.py` | Same | **Commit** |
| `Mercury_Enterprise_v16/backend/tests/test_decisions_api.py` | Same | **Commit** |
| `Mercury_Enterprise_v16/backend/tests/test_observability.py` | Login before gated platform/ops reads | **Commit** |
| `Mercury_Enterprise_v16/backend/tests/test_ops.py` | Ops coordinate auth matrix | **Commit** |
| `Mercury_Enterprise_v16/backend/tests/test_reporting.py` | `TEST_AUTH_PASSWORD` | **Commit** |
| `Mercury_Enterprise_v16/docker-compose.dev.yml` | Comment: published `:8000` is **dev-only** | **Commit** |
| `Mercury_Enterprise_v16/docker-compose.yml` | Comment: backend compose-network only | **Commit** |
| `Mercury_Enterprise_v16/docs/ARCHITECTURE.md` | Same-origin API/WS; single worker; Alembic note | **Commit** |
| `Mercury_Enterprise_v16/docs/SECURITY.md` | Align with env-required password / no auto-login | **Commit** |
| `Mercury_Enterprise_v16/docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md` | Hardening deploy/rollback steps | **Commit** |
| `Mercury_Enterprise_v16/frontend/Dockerfile` | Ensure empty `config.local.js` exists in image | **Commit** |
| `Mercury_Enterprise_v16/frontend/css/components.css` | Login overlay styles | **Commit** |
| `Mercury_Enterprise_v16/frontend/index.html` | V2.0/16.0.0 branding; login overlay; `config.local.js` script | **Commit** |
| `Mercury_Enterprise_v16/frontend/js/app.js` | Interactive login; remove demo auto-login; decision UI helpers | **Commit** |
| `Mercury_Enterprise_v16/frontend/js/commandCenter.js` | XSS `esc()` + version string | **Commit** |
| `Mercury_Enterprise_v16/frontend/js/config.js` | Same-origin `/api/v1` + override resolution (C1) | **Commit** |
| `Mercury_Enterprise_v16/frontend/js/enterprise.js` | Cleanup: shared `esc` / download helpers | **Commit** |
| `Mercury_Enterprise_v16/frontend/js/enterprise8.js` | Same + export version label | **Commit** |
| `Mercury_Enterprise_v16/frontend/js/liveOps.js` | XSS `esc()` (H5) | **Commit** |
| `Mercury_Enterprise_v16/frontend/js/utils.js` | Shared `esc` / `download` | **Commit** |
| `Mercury_Enterprise_v16/frontend/js/websocket.js` | Same-origin WS (C2) | **Commit** |

**Restore?** None of the modified paths above look accidental relative to approved hardening/cleanup. **No restore recommended** unless you explicitly want to drop a subset (e.g. omit design docs — those are untracked below).

---

## Deleted files (` D`)

| Path | Why | Action |
|------|-----|--------|
| `Mercury_Enterprise_v16/.github/workflows/ci.yml` | Relocate CI to git root | **Commit** deletion |
| `Mercury_Enterprise_v16/backend/app/security/api_key.py` | Dead unused API-key helper | **Commit** deletion |
| `Mercury_Enterprise_v16/backend/mercury.db` | Untrack runtime SQLite | **Commit** deletion |
| `Mercury_Enterprise_v16/mercury.db` | Untrack runtime SQLite | **Commit** deletion |
| `Mercury_Enterprise_v16/tmp_models.txt` | Remove temp scratch | **Commit** deletion |
| `Mercury_Enterprise_v16/tmp_schemas.txt` | Remove temp scratch | **Commit** deletion |

---

## Untracked files (`??`)

| Path | Why present | Action |
|------|-------------|--------|
| `.github/workflows/ci.yml` | Git-root CI (discoverable by Actions) | **Commit** (add) |
| `Mercury_Enterprise_v16/backend/alembic.ini` | H3 Postgres migration tooling | **Commit** |
| `Mercury_Enterprise_v16/backend/alembic/env.py` | Alembic env | **Commit** |
| `Mercury_Enterprise_v16/backend/alembic/script.py.mako` | Alembic template | **Commit** |
| `Mercury_Enterprise_v16/backend/alembic/versions/20260810_0001_baseline.py` | Baseline migration | **Commit** |
| `Mercury_Enterprise_v16/backend/tests/test_hardening_security.py` | Security verification tests | **Commit** |
| `Mercury_Enterprise_v16/docs/RELEASE_NOTES_v2.0.md` | Current V2.0 release notes | **Commit** |
| `Mercury_Enterprise_v16/docs/design/FINAL_CLEANUP_REPORT.md` | Cleanup evidence | **Commit** (release record) |
| `Mercury_Enterprise_v16/docs/design/FINAL_RELEASE_AUDIT.md` | Pre-hardening audit | **Commit** |
| `Mercury_Enterprise_v16/docs/design/FINAL_RELEASE_GATE.md` | Gate NO GO record | **Commit** |
| `Mercury_Enterprise_v16/docs/design/FINAL_RELEASE_VERIFICATION.md` | Verification v1 | **Commit** |
| `Mercury_Enterprise_v16/docs/design/FINAL_RELEASE_VERIFICATION_v2.md` | Verification v2 | **Commit** |
| `Mercury_Enterprise_v16/docs/design/PRODUCTION_HARDENING_REPORT.md` | Hardening delivery report | **Commit** |
| `Mercury_Enterprise_v16/docs/design/PRODUCTION_HARDENING_SPEC.md` | Approved hardening spec | **Commit** |
| `Mercury_Enterprise_v16/docs/design/PRODUCTION_VALIDATION_REPORT.md` | Pre-hardening validation | **Commit** |
| `Mercury_Enterprise_v16/docs/design/RC2_FINAL_ACTION_PLAN.md` | Post-hardening action plan | **Commit** |
| `Mercury_Enterprise_v16/frontend/js/config.local.js.example` | Local dual-process API/WS override template | **Commit** |
| `Mercury_Enterprise_v16/docs/design/FINAL_COMMIT_AUDIT.md` | **This file** (created by audit) | **Commit** once written |

### Explicitly **Ignore** (not in status, but must stay out)

| Path | Why |
|------|-----|
| `frontend/js/config.local.js` | Machine-local override; gitignored; created by `START_FRONTEND.bat` |
| `.env` | Secrets; gitignored |
| Any new `*.db` / `mercury*.db` | Runtime; gitignored after untrack commit |
| `__pycache__/`, `.pytest_cache/`, `.venv/` | Already ignored |

---

## Roll-up recommendation

| Bucket | Count (approx.) | Action |
|--------|-----------------|--------|
| Product / hardening / tests / packaging / launchers | All ` M` listed | **Commit** |
| Deletions (CI nest, api_key, DBs, tmp) | 6 | **Commit** |
| Untracked CI + Alembic + tests + design/release docs + config example | All `??` listed | **Commit** |
| Accidental / revert | **0** | **Restore** none |
| Runtime secrets / local overrides / DBs after untrack | N/A | **Ignore** |

### Suggested commit shape (for when you approve staging)

1. **One release commit** (or two: code+packaging, then docs-only) including:
   - Root `.github/workflows/ci.yml`
   - Nested CI deletion
   - Hardening code/tests/frontend
   - DB/tmp/`api_key.py` deletions
   - Alembic + release/design docs
2. Do **not** add `.env` or `config.local.js`.

### Stop point

**No staging or committing performed.** Awaiting your explicit approval before `git add` / `git commit`.
)
