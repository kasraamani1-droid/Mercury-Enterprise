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

For production / HTTPS also set `JWT_SECRET`, `COOKIE_SECRET`, `DOMAIN`, `HTTPS_ENABLED`, `LETSENCRYPT_EMAIL`. Generate secrets:

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
- Apply migrations: `cd backend; alembic upgrade head`

## 3c. Backend tests (optional)

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pytest tests/ -q
```

## Default operators

Operators are bootstrapped in-process from configuration (shared password unless changed via admin APIs):

| Operator | Role |
|----------|------|
| `admin` | Administrator |
| value of `MERCURY_AUTH_OPERATOR` (default `operator`) | Operator |
| `reviewer` | Reviewer |
| `viewer` | Viewer |

Sign in with the configured `MERCURY_AUTH_PASSWORD`.

## Next steps

- Production deploy → [DEPLOYMENT.md](DEPLOYMENT.md)
- Security baseline → [SECURITY.md](SECURITY.md)
- Observability → [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)
