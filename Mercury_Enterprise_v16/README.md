# Mercury Enterprise v15.0 — Full Source Foundation

Mercury v15.0 is a **working, production-oriented source foundation** of the Mercury command platform. It preserves the full simulated command-center experience while adding deployment, configuration, WebSocket, database, health-check, security-header, CI, and container foundations.

> **Important:** this package is not certified operational aviation/security software. UAV, aircraft, sensor, AI, weather, compliance, and mission data are simulated. Before real deployment, complete independent security, privacy, safety, regulatory, human-factors, and operational validation.

## Fastest Windows start (SQLite development mode)

1. Stop older Mercury windows with `STOP_MERCURY.bat`.
2. Run `CHECK_SYSTEM.bat`.
3. Run `START_ALL.bat`.
4. Open `http://localhost:3000`.
5. API docs: `http://127.0.0.1:8000/docs`.

## Container start (PostgreSQL reference deployment)

```powershell
copy .env.example .env
docker compose up --build
```

Open `http://localhost:3000`.

## Production foundations included

- FastAPI API with request IDs, response timing, readiness/health endpoints, structured logging, and CORS allow-listing
- SQLAlchemy with SQLite local mode and PostgreSQL container mode
- WebSocket event gateway with heartbeat and incident broadcasts
- Optional API-key protection for write operations
- NGINX frontend container and reverse-proxy configuration
- Docker Compose, persistent PostgreSQL volume, health checks, and restart policies
- GitHub Actions CI for tests, Python compilation, and JavaScript syntax
- Modular frontend with Command, Digital Twin, Radar, Executive, History, Admin, Cloud, Integrations, and Compliance workspaces
- Tests and production-readiness documentation

## Key endpoints

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/incidents`
- `POST /api/v1/incidents`
- `GET /api/v1/incidents/{id}`
- `PATCH /api/v1/incidents/{id}/status`
- `GET /api/v1/incidents/{id}/assessment`
- `GET /api/v1/incidents/{id}/report`
- `WS /api/v1/ws`

## Security note

Set `MERCURY_API_KEY` in production. The included API-key mechanism is a deployment baseline, not a substitute for enterprise SSO/OIDC, secrets management, network segmentation, WAF/rate limiting, signed audit events, or formal authorization policy.

See `docs/PRODUCTION_READINESS.md`, `docs/ARCHITECTURE.md`, and `docs/SECURITY.md`.


## Scope transparency

Read `IMPLEMENTATION_STATUS.md` for the exact boundary between runnable code, simulated features, and integrations that still require engineering and certification.
