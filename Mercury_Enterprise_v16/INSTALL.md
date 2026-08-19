# Install

## Prerequisites

| Mode | Requirements |
|------|----------------|
| Windows local | Python 3.11+ (3.13 supported), modern browser |
| Containers | Docker Engine + Compose v2 |
| Production HTTPS | Public DNS, ports 80/443, `pg_dump`/`openssl` tools for cert bootstrap |

## 1. Clone and enter package

```powershell
cd Mercury_Enterprise_v16
```

## 2. Configure environment

```powershell
copy .env.example .env
```

Set at minimum:

```env
MERCURY_AUTH_PASSWORD=<unique-secret-12+-chars-in-production>
```

For production / HTTPS also set `JWT_SECRET`, `COOKIE_SECRET`, `DOMAIN`, `HTTPS_ENABLED`, `LETSENCRYPT_EMAIL`, and a real OIDC client (`MERCURY_OIDC_*`). Generate secrets:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never commit `.env`.

## 3a. Windows local (SQLite)

```powershell
.\CHECK_SYSTEM.bat
.\START_ALL.bat
```

- UI: http://localhost:3000  
- API docs: http://127.0.0.1:8000/docs  

Stop with `.\STOP_MERCURY.bat`.

## 3b. Docker Compose (PostgreSQL)

```powershell
docker compose up --build
```

- UI / API via NGINX: http://localhost:3000  
- Migrations: backend image entrypoint runs `alembic upgrade head` for PostgreSQL. Manual: `cd backend; alembic upgrade head`. See [docs/engineering/POSTGRESQL_MIGRATIONS.md](docs/engineering/POSTGRESQL_MIGRATIONS.md).

## 3c. Backend tests (optional)

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pytest tests/ -q
```

## Default operators

LAN / demo seed (`MERCURY_SEED_DEMO=true`, typical local development) bootstraps a shared-password directory:

| Operator | Role |
|----------|------|
| `admin` | Administrator |
| value of `MERCURY_AUTH_OPERATOR` (default `operator`) | Operator |
| `reviewer` | Reviewer |
| `viewer` | Viewer |

Sign in with the configured `MERCURY_AUTH_PASSWORD`. These shared accounts are **not** production identities. Production startup refuses `MERCURY_SEED_DEMO=true` and, without that seed, only `admin` plus `MERCURY_AUTH_OPERATOR` are bootstrapped. Internet TLS requires OIDC — see [docs/pilot/PRODUCTION.md](docs/pilot/PRODUCTION.md).

## Next steps

- Commercial production (OIDC, TLS overlay, backups) → [docs/pilot/PRODUCTION.md](docs/pilot/PRODUCTION.md)
- Production deploy → [DEPLOYMENT.md](DEPLOYMENT.md)
- Security baseline → [SECURITY.md](SECURITY.md)
- Observability → [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)
