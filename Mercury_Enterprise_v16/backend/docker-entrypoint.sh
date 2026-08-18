#!/bin/sh
# Mercury AEOS backend entrypoint — apply Alembic before serving (PostgreSQL path).
set -eu

db_url="${DATABASE_URL:-}"

case "$db_url" in
  postgresql*|postgres*)
    echo "[mercury] DATABASE_URL is PostgreSQL — running alembic upgrade head"
    alembic upgrade head
    ;;
  *)
    echo "[mercury] DATABASE_URL is not PostgreSQL — skipping Alembic (dev SQLite uses ensure_schema)"
    ;;
esac

exec "$@"
