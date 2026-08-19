# Pilot security and network exposure

## What is exposed on the host (default Compose)

| Port | Service | Notes |
| --- | --- | --- |
| `3000` | Frontend NGINX | Static UI + same-origin `/api` reverse proxy. Health: `/live`, `/ready`, `/api/v1/ready` |
| — | `backend:8000` | Compose-network only (`expose`, not `ports`) |
| — | Postgres 5432 | Not published |
| — | Redis 6379 | Not published (commented ports in compose) |

This is a **trusted LAN or localhost** topology. Binding `:3000` accepts connections from the host network. Do not port-forward it to the public internet for a paid customer.

`docker-compose.dev.yml` publishes backend `:8000` for local debugging — do not use that overlay in a customer pilot.

## Auth, RBAC, tenants

- Session cookie (`mercury_session`). HTTP pilot requires `MERCURY_ENV=development` and `MERCURY_SESSION_COOKIE_SECURE=false`.
- Roles: Viewer read, Operator manage (and execute), Reviewer inspect/release, Administrator manage/admin.
- Organization isolation: requesting `org-aviation-west` as an East operator returns 403. Get-by-id cross-tenant reads return **404** (no existence oracle).
- Workforce mutations require `planning.manage`. GET-by-id is org-scoped.
- Demo users `operator` / `viewer` / `reviewer` share the password from local `.env`. They are **not** production identities. Production startup refuses `MERCURY_SEED_DEMO=true`.

## Secrets

Never commit `.env`, `config.local.js`, `*.db`, dumps, JWT, or cookie secrets. `.env.example` has empty password/secret fields. Backup archives can contain operational data — keep them off git (`backups/` is gitignored).

## Browser / API hardening already present

- NGINX security headers, login and API rate limits, same-origin API
- FastAPI CORS from `MERCURY_CORS_ORIGINS` (default `http://localhost:3000`). Same-origin UI does not need extra CORS for LAN IP access to `:3000`
- Operator UI uses `esc()` for DOM interpolation on workforce/planning desks

## Internet-facing production blockers (external steps remain)

| Item | Class |
| --- | --- |
| Real IdP client credentials (issuer, client id/secret, redirect URI) | **P0** — architecture is implemented; activation needs the customer IdP |
| Public DNS + Let's Encrypt issued certs for `$DOMAIN` | **P0** — nginx/TLS path exists; certs are not in git |
| Encrypted off-box backup copies + unique `POSTGRES_PASSWORD` | **P1** |
| Named (non-shared) operator identities for paid accountability | **P1** until OIDC directory is populated |

OIDC authorization-code + PKCE is implemented (`GET /api/v1/auth/oidc/login` and `/callback`). Password demo auth is disabled when HTTPS/OIDC is required. Do not treat `:3000` as the production public endpoint — use `docker-compose.production.yml` so only `:443` is published. See [PRODUCTION.md](PRODUCTION.md).
