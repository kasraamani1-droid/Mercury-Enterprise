# Mercury Enterprise V2.0 (package 16.0.0)

Mercury is a **working, production-oriented source foundation** of the Mercury command platform with simulated operational feeds.

> **Important:** not certified operational aviation/security software. Complete independent validation before real deployment.

## Documentation

| Guide | Description |
|-------|-------------|
| [INSTALL.md](INSTALL.md) | Local and container install |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production Compose / HTTPS deployment |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Runtime topology and modules |
| [SECURITY.md](SECURITY.md) | Authn/z, cookies, headers, secrets |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Branching, tests, PR expectations |
| [ROADMAP.md](ROADMAP.md) | Near-term and deferred work |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md) | Logs, health, metrics |
| [docs/ORGANIZATIONS.md](docs/ORGANIZATIONS.md) | Multi-tenant org hierarchy & RBAC |
| [docs/security/HTTPS.md](docs/security/HTTPS.md) | TLS / Let's Encrypt |

## Fastest Windows start (SQLite development)

1. Copy `.env.example` to `.env` and set `MERCURY_AUTH_PASSWORD` to a unique secret (not a demo/default value).
2. `STOP_MERCURY.bat` if needed, then `CHECK_SYSTEM.bat`, then `START_ALL.bat`.
3. Open `http://localhost:3000` and sign in with your configured operator password.
4. API docs: `http://127.0.0.1:8000/docs` (local dual-process; `config.local.js` points the UI at `:8000`).

## Container start (PostgreSQL)

```powershell
copy .env.example .env
# Set MERCURY_AUTH_PASSWORD (required) and DATABASE_URL
docker compose up --build
```

Open `http://localhost:3000` (NGINX proxies `/api` and WebSocket).

Postgres migrations: `cd backend; alembic upgrade head`

## Production HTTPS

```bash
# Set DOMAIN, HTTPS_ENABLED, LETSENCRYPT_EMAIL, JWT_SECRET, COOKIE_SECRET, MERCURY_AUTH_PASSWORD
sh deploy/init-letsencrypt.sh
docker compose --profile production up --build -d
```

See [DEPLOYMENT.md](DEPLOYMENT.md) and [docs/security/HTTPS.md](docs/security/HTTPS.md).

## Version identity

| Field | Value |
|-------|--------|
| Product | Mercury Enterprise V2.0 |
| Package / API (`MERCURY_VERSION`) | 16.0.0 |
| Security sprint | v0.9.1 (HTTPS / hardening) |
| Observability sprint | v0.9.2 (logs / metrics / admin / backup) |

See [docs/RELEASE_NOTES_v2.0.md](docs/RELEASE_NOTES_v2.0.md) and [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).
