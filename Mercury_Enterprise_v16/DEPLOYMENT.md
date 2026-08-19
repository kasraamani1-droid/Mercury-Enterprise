# Deployment

## Profiles

| Profile | Command | Exposure |
|---------|---------|----------|
| Default (lab) | `docker compose up --build` | `localhost:3000` HTTP |
| Production | `docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml up --build -d` | `:80` / `:443` via edge NGINX (`:3000` unpublished) |

## Production checklist

1. Copy `.env.example` → `.env` and set secrets (no insecure defaults).
2. Set `MERCURY_ENV=production`, `HTTPS_ENABLED=true`, `DOMAIN`, `LETSENCRYPT_EMAIL`.
3. Set `JWT_SECRET` and `COOKIE_SECRET` (≥32 unique characters).
4. Set `MERCURY_AUTH_MODE=oidc` and real `MERCURY_OIDC_ISSUER` / `CLIENT_ID` / `CLIENT_SECRET` / `REDIRECT_URI` (no placeholders).
5. Set `REDIS_URL` (Compose default `redis://redis:6379/0`). Production overlay forces `REDIS_REQUIRED=true`.
6. Set `POSTGRES_PASSWORD` (unique) and keep `DATABASE_URL` in sync. Set `MERCURY_CORS_ORIGINS=https://YOUR_DOMAIN`.
7. Point DNS A/AAAA for `DOMAIN` at the host; open ports **80** and **443**.
8. Bootstrap certificates:

```bash
export DOMAIN=mercury.example.com
export LETSENCRYPT_EMAIL=ops@example.com
sh deploy/init-letsencrypt.sh
```

9. Start stack:

```bash
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml up --build -d
```

10. Verify:

```bash
curl -fsS https://$DOMAIN/live
curl -fsS https://$DOMAIN/ready
curl -fsSI http://$DOMAIN/   # expect Location: https://...
```

Do not treat `:3000` as the public endpoint. Full TLS detail: [docs/security/HTTPS.md](docs/security/HTTPS.md). Commercial runbook: [docs/pilot/PRODUCTION.md](docs/pilot/PRODUCTION.md).

## Service health

Compose includes restart policies and healthchecks:

| Service | Probe |
|---------|--------|
| `postgres` | `pg_isready` |
| `backend` | `GET /ready` |
| `frontend` | `GET /live` |
| `nginx` (production) | `GET /live` on :80 |

## Database migrations

Production Compose sets `DATABASE_URL` to PostgreSQL. The backend image entrypoint runs:

```bash
alembic upgrade head
```

before uvicorn when `DATABASE_URL` starts with `postgresql` / `postgres`.

Manual (host tooling against a reachable Postgres):

```bash
cd backend
alembic upgrade head
alembic current   # expect head revision (e.g. 20260819_0023)
```

Procedure, rollback, dual SQLite bootstrap, and tests: [docs/engineering/POSTGRESQL_MIGRATIONS.md](docs/engineering/POSTGRESQL_MIGRATIONS.md).

## Backups

```bash
export DATABASE_URL=postgresql+psycopg://mercury:mercury@localhost:5432/mercury
export BACKUP_DIR=./backups
sh scripts/backup_database.sh
export BACKUP_FILE=./backups/<file>
sh scripts/verify_backup.sh
export MERCURY_RESTORE_CONFIRM=YES
# sh scripts/restore_database.sh
```

See [docs/BACKUP.md](docs/BACKUP.md).

## Observability endpoints

| Endpoint | Auth | Notes |
|----------|------|-------|
| `/live` `/ready` `/health` | none | Probes |
| `/metrics` | none | Prometheus — keep on Compose network |
| `/admin/system` `/admin/health` `/admin/metrics` `/admin/audit` | Administrator | Ops dashboard API |

## Rollback

```bash
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml down
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml up --build -d
```

Confirm `/ready` and operator login after rollback. Destructive database restore requires `MERCURY_RESTORE_CONFIRM=YES`.

## Related runbooks

- `docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md`
- `docs/runbooks/DISASTER_RECOVERY.md`
- `docs/runbooks/ADMINISTRATOR.md`
