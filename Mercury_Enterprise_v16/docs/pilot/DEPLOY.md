# Pilot deploy — start, stop, backup, restore

Trusted network only (localhost or LAN) unless you complete [PRODUCTION.md](PRODUCTION.md). Default Compose HTTP on `:3000` is **not** internet-facing production.

The TLS edge is `docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml` (unpublishes `:3000`). HTTPS deployments require OIDC. Internet-facing activation (DNS, certs, real IdP) is **OWNER ACTION REQUIRED** — see [ACTIVATION.md](ACTIVATION.md).

## Prerequisites

- Docker Compose in the package directory `Mercury_Enterprise_v16`
- A local `.env` copied from `.env.example` with **locally generated** secrets (`JWT_SECRET`, `COOKIE_SECRET`, `MERCURY_AUTH_PASSWORD` ≥ 12 characters). Never commit `.env`.
- HTTP on `:3000`: `MERCURY_ENV=development`, `MERCURY_SESSION_COOKIE_SECURE=false`, `MERCURY_SEED_DEMO=true`
- `DATABASE_URL` may stay `postgresql+psycopg://mercury:mercury@postgres:5432/mercury` (Compose service credentials, not a public database)

Demo session users created by seed: `operator`, `viewer`, `reviewer`. Set the shared password only in `.env`.

## Start (recreate app containers, keep data)

From the package directory:

```powershell
# Optional: dump before rebuild (Git Bash)
$env:MERCURY_BACKUP_VIA_COMPOSE = "1"
$env:DATABASE_URL = "postgresql+psycopg://mercury:mercury@postgres:5432/mercury"
$env:BACKUP_DIR = "./backups"
# bash scripts/backup_database.sh

docker compose up -d --build
```

`--build` rebuilds images and recreates app containers. Named volume `mercury_postgres` is kept unless you pass `-v`.

Health (existing endpoints only):

```powershell
curl.exe http://localhost:3000/live
curl.exe http://localhost:3000/api/v1/ready
```

UI: `http://localhost:3000` (or `http://<lan-ip>:3000` on the same trusted LAN). Same-origin `/api` — do not publish backend `:8000` for the pilot.

## Stop

```powershell
docker compose stop
```

`docker compose down` removes containers but keeps volumes. `docker compose down -v` **destroys** Postgres data — take a dump first.

## Backup

Existing scripts: `scripts/backup_database.sh`, `scripts/verify_backup.sh`, `scripts/restore_database.sh`. See [BACKUP.md](../BACKUP.md).

Compose Postgres is not published on the host. Use `MERCURY_BACKUP_VIA_COMPOSE=1` so the scripts `exec` `pg_dump` inside the `postgres` service.

Verify:

```bash
export BACKUP_FILE=./backups/mercury-postgres-….dump
sh scripts/verify_backup.sh
```

Store dumps **outside git**. `backups/` is gitignored.

## Restore

```bash
export MERCURY_BACKUP_VIA_COMPOSE=1
export DATABASE_URL=postgresql+psycopg://mercury:mercury@postgres:5432/mercury
export BACKUP_FILE=./backups/mercury-postgres-….dump
export MERCURY_RESTORE_CONFIRM=YES
sh scripts/restore_database.sh
```

Then hit `/api/v1/ready`. Seed is idempotent; restore replaces operational rows with the dump. Do not run restore against a live customer database without a fresh backup.

## Shutdown checklist

1. Backup (and checksum)
2. `docker compose stop` or `down` (no `-v` unless you intend to wipe)
3. Confirm `.env` and dumps are not in version control
