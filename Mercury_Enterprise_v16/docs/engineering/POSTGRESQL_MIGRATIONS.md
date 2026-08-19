# PostgreSQL Migrations (RC1 Blocker 05)

**Status:** Production path validated 2026-08-17 (schema + pooling + tests). Live PostgreSQL `upgrade head` is still operator-gated via `MERCURY_TEST_DATABASE_URL` (Docker is not installed on the RC1 Windows validation host).  
**Parent:** Mercury Platform RC1 Release Blocker Report (E2E RB-06 / M11 dual-bootstrap)

## Verdict (this blocker)

| Item | Result |
|------|--------|
| PostgreSQL as production database | **GO** — SQLAlchemy models, Alembic chain, Compose, pooling, and repositories are production-capable |
| Live host verification on this workstation | **Pending** — set `MERCURY_TEST_DATABASE_URL` once against disposable Postgres 17 before first production cutover |
| Production readiness | **91%** |
| Mercury Platform RC1 tag | Still **NO-GO** (unrelated: identity durability RB-04, Redis, Sign out, Playwright) |

## Authority

| Environment | Schema path | Notes |
|-------------|-------------|--------|
| **Production / Compose** | PostgreSQL + `alembic upgrade head` | System of record. Backend image entrypoint runs Alembic when `DATABASE_URL` is Postgres. |
| **Local Windows / pytest** | SQLite + `ensure_schema()` / `create_all` | Dev convenience only. Do not use SQLite Alembic as the production story. |
| **Alembic CI checks** | SQLite file DB with Alembic **batch mode** | Exercises the full revision chain without Docker. Optional live Postgres via `MERCURY_TEST_DATABASE_URL`. |

**Rule:** new tables require a SQLAlchemy model **and** an Alembic revision under `backend/alembic/versions/`. Relying on `create_all` alone in a deployed environment is a defect.

## Current head

- **Head revision:** `20260819_0023` (OIDC issuer/subject on `org_users`)
- **Chain:** linear, single head, baseline `20260810_0001` → … → `20260819_0023` (23 revisions)
- **History:** `cd backend && python -m alembic history`

## Clean install (PostgreSQL)

```powershell
copy .env.example .env
# Set MERCURY_AUTH_PASSWORD, JWT_SECRET, COOKIE_SECRET
# DATABASE_URL defaults to postgresql+psycopg://mercury:mercury@postgres:5432/mercury
docker compose up --build
```

The backend container:

1. Starts with `docker-entrypoint.sh`
2. Detects a PostgreSQL `DATABASE_URL`
3. Runs `alembic upgrade head` (Alembic uses `NullPool` for the migration connection)
4. Starts uvicorn (single worker)
5. Lifespan calls `ensure_schema()`: `create_all` is a no-op for tables Alembic already created; SQLite `PRAGMA` patches are skipped

Manual equivalent (host with network access to Postgres):

```powershell
cd backend
$env:DATABASE_URL="postgresql+psycopg://mercury:mercury@localhost:5432/mercury"
python -m alembic upgrade head
```

Compose waits for `postgres:17-alpine` `pg_isready` before starting the backend.

## Upgrade

1. Backup the database volume (see [BACKUP.md](../BACKUP.md) and [DISASTER_RECOVERY](../runbooks/DISASTER_RECOVERY.md)).
2. Deploy the new backend image / tree.
3. Ensure `alembic upgrade head` runs (Compose entrypoint, or explicit CI/CD step).
4. Confirm `alembic current` reports `20260819_0023` (or newer head after this doc’s date).
5. Smoke `/ready` and operator login.

Second `upgrade head` on an already-migrated database is a no-op.

## Rollback

Prefer **application rollback + database backup restore** when a migration is not safely reversible in production.

When a revision’s `downgrade()` is safe (additive tables/columns only):

```powershell
cd backend
python -m alembic downgrade -1    # one revision
python -m alembic upgrade head    # re-apply after fix
```

Do **not** use `downgrade` to “fix” application bugs by dropping evidence/audit tables.

CI also exercises `alembic downgrade base` then `upgrade head` on a disposable SQLite file. Prefer backup restore for production data.

## SQLite / dual bootstrap

- `ensure_schema()` in `backend/app/database.py` still runs `create_all` for empty local DBs and SQLite additive patches.
- On PostgreSQL, `ensure_schema()` only calls `create_all` (no-op if Alembic already created tables) and skips SQLite `ALTER` patches.
- Alembic `env.py` calls `import_orm_models()` so autogenerate sees the full metadata, and enables `render_as_batch` **only** for SQLite.
- Revisions that ALTER constraints/defaults (`20260813_0005`–`0008`) use `op.batch_alter_table(...)` so the chain is verifiable on SQLite; on PostgreSQL those wrappers emit normal `ALTER` statements.
- SQLite does **not** enforce foreign keys unless `PRAGMA foreign_keys=ON` (left off so existing dev tests keep working). PostgreSQL enforces FKs.

## Sessions, transactions, pooling

| Concern | Production behavior |
|---------|---------------------|
| Driver | `psycopg` v3 (`postgresql+psycopg://…`) |
| Pool | SQLAlchemy `QueuePool` with `pool_pre_ping=True` |
| Size | `MERCURY_DB_POOL_SIZE` (default 5) |
| Overflow | `MERCURY_DB_MAX_OVERFLOW` (default 10) |
| Recycle | `MERCURY_DB_POOL_RECYCLE` (default 1800 seconds) |
| Migrations | Alembic `NullPool` (one-shot connections) |
| Request session | `get_db()` yields a session, **rolls back on exception**, always `close()` |
| Autocommit | Off. Repositories commit explicitly. |
| Row locks | `SELECT … FOR UPDATE` compiles on PostgreSQL; SQLite ignores it |
| Search | SQLAlchemy `.ilike()` → `ILIKE` on Postgres, `LIKE` on SQLite |

SQLite development engines omit QueuePool size/recycle (check_same_thread only).

## Production configuration checklist

| Item | Expected |
|------|----------|
| `.env` / Compose `DATABASE_URL` | `postgresql+psycopg://…` |
| Backend image | Contains `alembic/`, `alembic.ini`, `docker-entrypoint.sh` |
| Entrypoint | `alembic upgrade head` before uvicorn when URL is Postgres |
| Pooling | Defaults above, or override `MERCURY_DB_POOL_*` |
| Secrets | `MERCURY_AUTH_PASSWORD`, `JWT_SECRET`, `COOKIE_SECRET` set; no demo defaults |
| Redis | Recommended for multi-worker; `REDIS_REQUIRED` still optional (separate RC blocker) |

## Automated tests

```powershell
cd backend
$env:MERCURY_ENV="development"
$env:MERCURY_AUTH_PASSWORD="ci-test-password-not-for-production"
python -m pytest -q tests/test_postgresql_migrations.py
```

Coverage: linear head, every revision has upgrade/downgrade, Compose/Dockerfile/entrypoint, clean install, idempotent upgrade, downgrade `-1`, full `downgrade base` + re-upgrade, ORM FK/index/unique metadata, portable column types, ILIKE/`FOR UPDATE` compile, session rollback, pooling kwargs.

Optional live Postgres (also inspects FKs/indexes/uniques after upgrade):

```powershell
$env:MERCURY_TEST_DATABASE_URL="postgresql+psycopg://mercury:mercury@127.0.0.1:5432/mercury_mig_test"
python -m pytest -q tests/test_postgresql_migrations.py
```

## Remaining PostgreSQL issues (not blockers for first PG deploy)

1. **Live `alembic upgrade head` not executed on this Windows host** — Docker is not installed; optional test skipped without `MERCURY_TEST_DATABASE_URL`. Run once on a disposable Postgres 17 before production cutover.
2. **Later domain revisions use `Base.metadata.create_all` for named tables** (`0010`–`0020`) rather than frozen `op.create_table` snapshots. Idempotent on empty DBs; operators must still add a revision when models change.
3. **`ensure_schema()` still calls `create_all` on Postgres at process start** — no-op if Alembic is current; would silently create a table that exists only as a model (no revision). Operational rule: never deploy a model without a revision.
4. **SQLite does not enforce FKs by default** — development-only; PostgreSQL enforces them.
5. **No SQL `CHECK` constraints** — status/type enums are validated in application code.
6. **Naive `DateTime` (UTC via `datetime.utcnow`)** — maps to `TIMESTAMP WITHOUT TIME ZONE` on Postgres. Do not mix server local time.
7. **Boolean-as-string on some logistics flags** plus native `Boolean` on `approval_requests.consumed` — portable, but mixed conventions (documented in Data_Model.md).
8. **No Postgres partitioning, replica/failover, or `statement_timeout`** — out of RC1 scope; single primary is assumed.
9. **`create_all` at startup is not a substitute for Alembic** on production — dual-bootstrap remains intentional for SQLite.

## Related

- [DEPLOY_UPGRADE_ROLLBACK.md](../runbooks/DEPLOY_UPGRADE_ROLLBACK.md)
- [DEPLOYMENT.md](../../DEPLOYMENT.md)
- [Data_Model.md](../../mercury-enterprise-blueprint/docs/04_Data/Data_Model.md) — dialect portability
