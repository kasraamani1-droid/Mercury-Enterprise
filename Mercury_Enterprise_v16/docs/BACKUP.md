# Backup & Restore

Scripts live under `scripts/` and support PostgreSQL (Compose production) and SQLite (local development).

## Backup

```bash
export DATABASE_URL=postgresql+psycopg://mercury:mercury@localhost:5432/mercury
export BACKUP_DIR=./backups
sh scripts/backup_database.sh
```

Creates a timestamped file plus `.sha256` checksum:

- PostgreSQL → `mercury-postgres-<UTC>.dump` (`pg_dump --format=custom`)
- SQLite → `mercury-sqlite-<UTC>.db`

## Verify

```bash
export BACKUP_FILE=./backups/mercury-postgres-YYYYMMDDThhmmssZ.dump
sh scripts/verify_backup.sh
```

Checks size, checksum, and (when tools exist) `pg_restore --list` or SQLite `integrity_check`.

## Restore

```bash
export DATABASE_URL=postgresql+psycopg://mercury:mercury@localhost:5432/mercury
export BACKUP_FILE=./backups/mercury-postgres-YYYYMMDDThhmmssZ.dump
export MERCURY_RESTORE_CONFIRM=YES
sh scripts/restore_database.sh
```

PostgreSQL restore uses `pg_restore --clean --if-exists`. SQLite restore replaces the target DB file.

Destructive restore is refused unless:

```bash
export MERCURY_RESTORE_CONFIRM=YES
```

## Encryption at rest

Optional archive encryption (openssl AES-256-CBC, PBKDF2). Create a key file that is **never** committed:

```bash
python -c "import secrets; open('backup.key','w').write(secrets.token_urlsafe(48))"
export MERCURY_BACKUP_KEY_FILE=./backup.key
sh scripts/backup_database.sh
```

Produces `*.dump.enc` or `*.db.enc` plus checksum. Restore uses the same `MERCURY_BACKUP_KEY_FILE`.

Retention (optional): `MERCURY_BACKUP_RETAIN_DAYS=14`.

**Off-box / provider boundary:** copy encrypted archives to object storage, offline media, or the cloud provider’s backup product **that you already operate**. This repository does not create a bucket or invent a cloud account. Compose volume `mercury_postgres` is not encrypted by Mercury itself — use host BitLocker/LUKS or encrypted cloud disks.

## Compose (pilot)

Default `docker-compose.yml` does **not** publish Postgres. Backup from the host with:

```bash
export MERCURY_BACKUP_VIA_COMPOSE=1
export DATABASE_URL=postgresql+psycopg://mercury:mercury@postgres:5432/mercury
export BACKUP_DIR=./backups
sh scripts/backup_database.sh
```

The scripts call `docker compose exec` `pg_dump` / `docker compose cp` + `pg_restore` inside the `postgres` service. Restore:

```bash
export MERCURY_BACKUP_VIA_COMPOSE=1
export DATABASE_URL=postgresql+psycopg://mercury:mercury@postgres:5432/mercury
export BACKUP_FILE=./backups/mercury-postgres-YYYYMMDDThhmmssZ.dump
export MERCURY_RESTORE_CONFIRM=YES
sh scripts/restore_database.sh
```

On Windows, run the `sh` scripts from Git Bash so custom-format dumps stay binary-safe. PowerShell `>` redirection can corrupt `pg_dump -Fc` output.

Volume `mercury_postgres` is not a substitute for `pg_dump` backups. Take a dump (and optionally a volume tarball) before `docker compose up -d --build`. Recreating containers does not destroy the named volume; `docker compose down -v` does.

## Operations tips

1. Take a backup before upgrades and before destructive admin changes.
2. Store checksums with the archive.
3. Periodically restore into a staging database and hit `/ready`.
4. Compose volume `mercury_postgres` is not a substitute for `pg_dump` backups.
