#!/usr/bin/env sh
# Backup Mercury PostgreSQL (or SQLite file) to a timestamped archive.
# Usage:
#   DATABASE_URL=postgresql+psycopg://mercury:mercury@localhost:5432/mercury \
#   BACKUP_DIR=./backups sh scripts/backup_database.sh

set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

DATABASE_URL="${DATABASE_URL:-}"
if [ -z "$DATABASE_URL" ] && [ -f "$ROOT/.env" ]; then
  # shellcheck disable=SC1091
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$ROOT/.env" | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
fi

if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

case "$DATABASE_URL" in
  sqlite*)
    # sqlite:///./mercury.db or sqlite:////abs/path
    DB_PATH="$(printf '%s' "$DATABASE_URL" | sed -E 's#^sqlite([0-9])?:///##; s#^\./##')"
    if [ ! -f "$DB_PATH" ]; then
      # Common package layouts
      if [ -f "$ROOT/backend/mercury.db" ]; then
        DB_PATH="$ROOT/backend/mercury.db"
      elif [ -f "$ROOT/mercury.db" ]; then
        DB_PATH="$ROOT/mercury.db"
      else
        echo "SQLite database file not found for $DATABASE_URL" >&2
        exit 1
      fi
    fi
    OUT="$BACKUP_DIR/mercury-sqlite-$STAMP.db"
    cp "$DB_PATH" "$OUT"
    sha256sum "$OUT" > "$OUT.sha256" 2>/dev/null || shasum -a 256 "$OUT" > "$OUT.sha256"
    echo "$OUT"
    ;;
  postgresql*|postgres*)
    # Convert SQLAlchemy URL to libpq-friendly pieces.
    # postgresql+psycopg://user:pass@host:port/db
    CLEAN="$(printf '%s' "$DATABASE_URL" | sed -E 's#^postgresql\+psycopg#postgresql#; s#^postgres\+psycopg#postgres#')"
    OUT="$BACKUP_DIR/mercury-postgres-$STAMP.dump"
    if ! command -v pg_dump >/dev/null 2>&1; then
      echo "pg_dump is required for PostgreSQL backups" >&2
      exit 1
    fi
    pg_dump --format=custom --file="$OUT" "$CLEAN"
    sha256sum "$OUT" > "$OUT.sha256" 2>/dev/null || shasum -a 256 "$OUT" > "$OUT.sha256"
    echo "$OUT"
    ;;
  *)
    echo "Unsupported DATABASE_URL scheme: $DATABASE_URL" >&2
    exit 1
    ;;
esac
