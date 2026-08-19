#!/usr/bin/env sh
# Verify a Mercury backup archive and its checksum.
# Usage:
#   BACKUP_FILE=./backups/mercury-postgres-....dump sh scripts/verify_backup.sh

set -eu

BACKUP_FILE="${BACKUP_FILE:-}"
if [ -z "$BACKUP_FILE" ]; then
  echo "BACKUP_FILE is required" >&2
  exit 1
fi
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

SIZE="$(wc -c < "$BACKUP_FILE" | tr -d ' ')"
if [ "$SIZE" -le 0 ]; then
  echo "Backup file is empty" >&2
  exit 1
fi

if [ -f "$BACKUP_FILE.sha256" ]; then
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "$BACKUP_FILE.sha256"
  else
    EXPECTED="$(awk '{print $1}' "$BACKUP_FILE.sha256")"
    ACTUAL="$(shasum -a 256 "$BACKUP_FILE" | awk '{print $1}')"
    if [ "$EXPECTED" != "$ACTUAL" ]; then
      echo "Checksum mismatch" >&2
      exit 1
    fi
    echo "Checksum OK"
  fi
else
  echo "WARNING: missing $BACKUP_FILE.sha256 — size check only ($SIZE bytes)"
fi

case "$BACKUP_FILE" in
  *.enc)
    echo "WARNING: encrypted backup — checksum only (decrypt before pg_restore/sqlite checks)"
    ;;
  *.dump)
    if command -v pg_restore >/dev/null 2>&1; then
      pg_restore --list "$BACKUP_FILE" >/dev/null
      echo "pg_restore --list OK"
    else
      echo "WARNING: pg_restore not available; skipped dump listing"
    fi
    ;;
  *.db)
    if command -v sqlite3 >/dev/null 2>&1; then
      sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q '^ok$'
      echo "SQLite integrity_check OK"
    else
      echo "WARNING: sqlite3 not available; skipped integrity_check"
    fi
    ;;
esac

echo "Backup verification passed: $BACKUP_FILE ($SIZE bytes)"
