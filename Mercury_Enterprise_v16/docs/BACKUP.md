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
sh scripts/restore_database.sh
```

PostgreSQL restore uses `pg_restore --clean --if-exists`. SQLite restore replaces the target DB file.

## Operations tips

1. Take a backup before upgrades and before destructive admin changes.
2. Store checksums with the archive.
3. Periodically restore into a staging database and hit `/ready`.
4. Compose volume `mercury_postgres` is not a substitute for `pg_dump` backups.
