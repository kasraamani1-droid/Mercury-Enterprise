#!/usr/bin/env sh
# Restore Mercury database from a backup created by backup_database.sh.
# Usage:
#   BACKUP_FILE=./backups/mercury-postgres-....dump \
#   DATABASE_URL=postgresql+psycopg://mercury:mercury@localhost:5432/mercury \
#   sh scripts/restore_database.sh

set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
BACKUP_FILE="${BACKUP_FILE:-}"
if [ -z "$BACKUP_FILE" ]; then
  echo "BACKUP_FILE is required" >&2
  exit 1
fi
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

DATABASE_URL="${DATABASE_URL:-}"
if [ -z "$DATABASE_URL" ] && [ -f "$ROOT/.env" ]; then
  # shellcheck disable=SC1091
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$ROOT/.env" | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
fi
if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

case "$BACKUP_FILE" in
  *.db)
    DB_PATH="$(printf '%s' "$DATABASE_URL" | sed -E 's#^sqlite([0-9])?:///##; s#^\./##')"
    if [ -z "$DB_PATH" ] || [ "$DB_PATH" = "$DATABASE_URL" ]; then
      DB_PATH="$ROOT/backend/mercury.db"
    fi
    mkdir -p "$(dirname "$DB_PATH")"
    cp "$BACKUP_FILE" "$DB_PATH"
    echo "Restored SQLite database to $DB_PATH"
    ;;
  *.dump)
    if ! command -v pg_restore >/dev/null 2>&1; then
      echo "pg_restore is required for PostgreSQL restores" >&2
      exit 1
    fi
    CLEAN="$(printf '%s' "$DATABASE_URL" | sed -E 's#^postgresql\+psycopg#postgresql#; s#^postgres\+psycopg#postgres#')"
    pg_restore --clean --if-exists --no-owner --dbname="$CLEAN" "$BACKUP_FILE"
    echo "Restored PostgreSQL database from $BACKUP_FILE"
    ;;
  *)
    echo "Unrecognized backup format: $BACKUP_FILE" >&2
    exit 1
    ;;
esac
