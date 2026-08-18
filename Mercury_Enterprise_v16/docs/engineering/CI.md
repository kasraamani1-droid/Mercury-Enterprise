# Continuous Integration

**Git root:** parent folder `Mercury_Enterprise_v16/` (contains `.git` and `.github/`).  
**Application package:** nested `Mercury_Enterprise_v16/Mercury_Enterprise_v16/` (this tree).

## Workflow

File: `../.github/workflows/ci.yml` (relative to this package) /  
`Mercury_Enterprise_v16/.github/workflows/ci.yml` from the download root.

Defaults:

```yaml
defaults:
  run:
    working-directory: Mercury_Enterprise_v16
```

Jobs:

1. `pip install -r backend/requirements.txt`
2. `python -m pytest -q backend/tests`
3. `python -m compileall backend/app`
4. Frontend `node --check` on `frontend/js/**/*.js` except gitignored `config.local.js`
5. Best-effort `docker compose config` / `build` (`continue-on-error: true`)

Linting (ruff/eslint) and type checkers (mypy) are **not** part of this pipeline.

## Local parity

```powershell
cd Mercury_Enterprise_v16\Mercury_Enterprise_v16
$env:MERCURY_AUTH_PASSWORD="ci-test-password-not-for-production"
$env:MERCURY_ENV="development"
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
python -m pip install -r backend/requirements.txt
python -m pytest -q backend/tests
python -m compileall backend/app
Get-ChildItem -Path frontend/js -Filter *.js -Recurse |
  Where-Object { $_.Name -ne 'config.local.js' } |
  ForEach-Object { node --check $_.FullName }
```

## Notes

- Redis is optional locally (`REDIS_REQUIRED=false`). Compose includes a Redis service for multi-worker sessions.
- CI does not start Redis; session tests use the in-memory backend.
- Alembic migration checks live in `backend/tests/test_postgresql_migrations.py` (SQLite batch mode plus pooling/FK/index/rollback tests). Optional live Postgres: set `MERCURY_TEST_DATABASE_URL`. See [POSTGRESQL_MIGRATIONS.md](POSTGRESQL_MIGRATIONS.md).
- Sequential RC1 smoke: `backend/tests/test_rc1_e2e_smoke.py`. Report: [RC1_SMOKE_TEST.md](RC1_SMOKE_TEST.md).
- **QA-1 closed:** work-order demo seed (`WP-DEMO-001` / `JC-DEMO-001`) is asserted in `test_work_orders_execution.py`; full suite is the CI gate.
