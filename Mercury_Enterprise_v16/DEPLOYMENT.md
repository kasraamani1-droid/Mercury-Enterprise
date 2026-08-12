# Deployment

## Profiles

| Profile | Command | Exposure |
|---------|---------|----------|
| Default (lab) | `docker compose up --build` | `localhost:3000` HTTP |
| Production | `docker compose --profile production up --build -d` | `:80` / `:443` via edge NGINX |

## Production checklist

1. Copy `.env.example` → `.env` and set secrets (no insecure defaults).
2. Set `MERCURY_ENV=production`, `HTTPS_ENABLED=true`, `DOMAIN`, `LETSENCRYPT_EMAIL`.
3. Set `JWT_SECRET` and `COOKIE_SECRET` (≥32 unique characters).
4. Set `MERCURY_CORS_ORIGINS=https://YOUR_DOMAIN`.
5. Point DNS A/AAAA for `DOMAIN` at the host; open ports **80** and **443**.
6. Bootstrap certificates:

```bash
export DOMAIN=mercury.example.com
export LETSENCRYPT_EMAIL=ops@example.com
sh deploy/init-letsencrypt.sh
```

7. Start stack:

```bash
docker compose --profile production up --build -d
```

8. Verify:

```bash
curl -fsS https://$DOMAIN/live
curl -fsS https://$DOMAIN/ready
curl -fsSI http://$DOMAIN/   # expect Location: https://...
```

Full TLS detail: [docs/security/HTTPS.md](docs/security/HTTPS.md).

## Service health

Compose includes restart policies and healthchecks:

| Service | Probe |
|---------|--------|
| `postgres` | `pg_isready` |
| `backend` | `GET /ready` |
| `frontend` | `GET /live` |
| `nginx` (production) | `GET /live` on :80 |

## Database migrations

```bash
cd backend
alembic upgrade head
```

## Backups

```bash
export DATABASE_URL=postgresql+psycopg://mercury:mercury@localhost:5432/mercury
export BACKUP_DIR=./backups
sh scripts/backup_database.sh
export BACKUP_FILE=./backups/<file>
sh scripts/verify_backup.sh
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
docker compose --profile production down
docker compose up --build -d
```

Confirm `/ready` and operator login after rollback.

## Related runbooks

- `docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md`
- `docs/runbooks/DISASTER_RECOVERY.md`
- `docs/runbooks/ADMINISTRATOR.md`
