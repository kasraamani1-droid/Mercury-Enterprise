# Mercury Enterprise V2.0 (package 16.0.0)

Mercury is a **working, production-oriented source foundation** of the Mercury command platform with simulated operational feeds.

> **Important:** not certified operational aviation/security software. Complete independent validation before real deployment.

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

## Version identity

| Field | Value |
|-------|--------|
| Product | Mercury Enterprise V2.0 |
| Package / API (`MERCURY_VERSION`) | 16.0.0 |

See `docs/RELEASE_NOTES_v2.0.md`, `docs/SECURITY.md`, and `IMPLEMENTATION_STATUS.md`.
