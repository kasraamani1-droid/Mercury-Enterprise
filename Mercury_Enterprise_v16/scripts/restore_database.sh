#!/usr/bin/env sh
# Restore Mercury database from a backup created by backup_database.sh.
# Usage:
#   BACKUP_FILE=./backups/mercury-postgres-....dump \
#   DATABASE_URL=postgresql+psycopg://mercury:mercury@localhost:5432/mercury \
#   sh scripts/restore_database.sh

set -eu

umask 077

DECRYPT_TMP=""
cleanup_decrypt_tmp() {
  if [ -n "${DECRYPT_TMP:-}" ] && [ -f "$DECRYPT_TMP" ]; then
    rm -f "$DECRYPT_TMP"
  fi
}
trap cleanup_decrypt_tmp EXIT

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
BACKUP_FILE="${BACKUP_FILE:-}"
if [ -z "$BACKUP_FILE" ]; then
  echo "BACKUP_FILE is required" >&2
  exit 1
fi
if [ "${MERCURY_RESTORE_CONFIRM:-}" != "YES" ]; then
  echo "Refusing destructive restore. Set MERCURY_RESTORE_CONFIRM=YES to proceed." >&2
  exit 1
fi
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

RESTORE_KIND=""
case "$BACKUP_FILE" in
  *.db|*.db.enc) RESTORE_KIND="sqlite" ;;
  *.dump|*.dump.enc) RESTORE_KIND="postgres" ;;
  *)
    echo "Unrecognized backup format: $BACKUP_FILE" >&2
    exit 1
    ;;
esac

decrypt_if_needed() {
  case "$BACKUP_FILE" in
    *.enc)
      key_file="${MERCURY_BACKUP_KEY_FILE:-}"
      if [ -z "$key_file" ] || [ ! -f "$key_file" ]; then
        echo "Encrypted backup requires MERCURY_BACKUP_KEY_FILE" >&2
        exit 1
      fi
      if ! command -v openssl >/dev/null 2>&1; then
        echo "openssl is required to decrypt backups" >&2
        exit 1
      fi
      tmp="$(mktemp)"
      DECRYPT_TMP="$tmp"
      openssl enc -d -aes-256-cbc -pbkdf2 -in "$BACKUP_FILE" -out "$tmp" -pass "file:$key_file"
      BACKUP_FILE="$tmp"
      ;;
  esac
}

decrypt_if_needed

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

case "$RESTORE_KIND" in
  sqlite)
    DB_PATH="$(printf '%s' "$DATABASE_URL" | sed -E 's#^sqlite([0-9])?:///##; s#^\./##')"
    if [ -z "$DB_PATH" ] || [ "$DB_PATH" = "$DATABASE_URL" ]; then
      DB_PATH="$ROOT/backend/mercury.db"
    fi
    mkdir -p "$(dirname "$DB_PATH")"
    cp "$BACKUP_FILE" "$DB_PATH"
    echo "Restored SQLite database to $DB_PATH"
    ;;
  postgres)
    if use_compose_postgres; then
      if ! command -v docker >/dev/null 2>&1; then
        echo "docker is required for Compose PostgreSQL restores" >&2
        exit 1
      fi
      docker compose -f "$(compose_file)" cp "$BACKUP_FILE" postgres:/tmp/mercury-restore.dump
      docker compose -f "$(compose_file)" exec -T postgres pg_restore --clean --if-exists --no-owner -U mercury -d mercury /tmp/mercury-restore.dump
      echo "Restored Compose PostgreSQL database from $BACKUP_FILE"
    else
      if ! command -v pg_restore >/dev/null 2>&1; then
        echo "pg_restore is required for PostgreSQL restores" >&2
        exit 1
      fi
      CLEAN="$(printf '%s' "$DATABASE_URL" | sed -E 's#^postgresql\+psycopg#postgresql#; s#^postgres\+psycopg#postgres#')"
      pg_restore --clean --if-exists --no-owner --dbname="$CLEAN" "$BACKUP_FILE"
      echo "Restored PostgreSQL database from $BACKUP_FILE"
    fi
    ;;
  *)
    echo "Unrecognized backup format: $BACKUP_FILE" >&2
    exit 1
    ;;
esac
