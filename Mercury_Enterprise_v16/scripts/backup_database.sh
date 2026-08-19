#!/usr/bin/env sh
# Backup Mercury PostgreSQL (or SQLite file) to a timestamped archive.
# Usage:
#   DATABASE_URL=postgresql+psycopg://mercury:mercury@localhost:5432/mercury \
#   BACKUP_DIR=./backups sh scripts/backup_database.sh

set -eu

umask 077

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR" 2>/dev/null || true

DATABASE_URL="${DATABASE_URL:-}"
if [ -z "$DATABASE_URL" ] && [ -f "$ROOT/.env" ]; then
  # shellcheck disable=SC1091
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$ROOT/.env" | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
fi

if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

compose_file() {
  if [ -f "$ROOT/docker-compose.yml" ]; then
    printf '%s' "$ROOT/docker-compose.yml"
  else
    printf '%s' "$ROOT/docker-compose.yaml"
  fi
}

use_compose_postgres() {
  [ "${MERCURY_BACKUP_VIA_COMPOSE:-}" = "1" ] && return 0
  printf '%s' "$DATABASE_URL" | grep -Eq '@postgres(:|[/?])|://postgres(:|[/?])' && return 0
  return 1
}

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
    ;;
  postgresql*|postgres*)
    # Convert SQLAlchemy URL to libpq-friendly pieces.
    # postgresql+psycopg://user:pass@host:port/db
    CLEAN="$(printf '%s' "$DATABASE_URL" | sed -E 's#^postgresql\+psycopg#postgresql#; s#^postgres\+psycopg#postgres#')"
    OUT="$BACKUP_DIR/mercury-postgres-$STAMP.dump"
    if use_compose_postgres; then
      if ! command -v docker >/dev/null 2>&1; then
        echo "docker is required for Compose PostgreSQL backups" >&2
        exit 1
      fi
      docker compose -f "$(compose_file)" exec -T postgres pg_dump -U mercury -Fc mercury > "$OUT"
    else
      if ! command -v pg_dump >/dev/null 2>&1; then
        echo "pg_dump is required for PostgreSQL backups" >&2
        exit 1
      fi
      pg_dump --format=custom --file="$OUT" "$CLEAN"
    fi
    sha256sum "$OUT" > "$OUT.sha256" 2>/dev/null || shasum -a 256 "$OUT" > "$OUT.sha256"
    ;;
  *)
    echo "Unsupported DATABASE_URL scheme: $DATABASE_URL" >&2
    exit 1
    ;;
esac

if [ ! -f "$OUT" ]; then
  echo "Backup file was not created" >&2
  exit 1
fi
chmod 600 "$OUT" "$OUT.sha256" 2>/dev/null || true

encrypt_backup() {
  key_file="${MERCURY_BACKUP_KEY_FILE:-}"
  if [ -z "$key_file" ]; then
    return 0
  fi
  if [ ! -f "$key_file" ]; then
    echo "MERCURY_BACKUP_KEY_FILE not found: $key_file" >&2
    exit 1
  fi
  if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required to encrypt backups when MERCURY_BACKUP_KEY_FILE is set" >&2
    exit 1
  fi
  enc="$OUT.enc"
  openssl enc -aes-256-cbc -pbkdf2 -salt -in "$OUT" -out "$enc" -pass "file:$key_file"
  chmod 600 "$enc"
  rm -f "$OUT"
  sha256sum "$enc" > "$enc.sha256" 2>/dev/null || shasum -a 256 "$enc" > "$enc.sha256"
  chmod 600 "$enc.sha256" 2>/dev/null || true
  OUT="$enc"
}

encrypt_backup

retain="${MERCURY_BACKUP_RETAIN_DAYS:-0}"
if [ "$retain" -gt 0 ] 2>/dev/null; then
  find "$BACKUP_DIR" -type f \( -name 'mercury-postgres-*' -o -name 'mercury-sqlite-*' \) -mtime "+$retain" -delete 2>/dev/null || true
fi

echo "$OUT"
