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
- Organization isolation: requesting `org-aviation-west` as an East operator returns 403.
- Workforce mutations require `planning.manage`. GET-by-id is org-scoped.
- Demo users `operator` / `viewer` / `reviewer` share the password from local `.env`. They are **not** production identities.

## Secrets

Never commit `.env`, `config.local.js`, `*.db`, dumps, JWT, or cookie secrets. `.env.example` has empty password/secret fields. Backup archives can contain operational data — keep them off git (`backups/` is gitignored).

## Browser / API hardening already present

- NGINX security headers, login and API rate limits, same-origin API
- FastAPI CORS from `MERCURY_CORS_ORIGINS` (default `http://localhost:3000`). Same-origin UI does not need extra CORS for LAN IP access to `:3000`
- Operator UI uses `esc()` for DOM interpolation on workforce/planning desks

## Internet-facing production blockers (not in this cycle)

| Item | Class |
| --- | --- |
| OIDC/SSO (or equivalent enterprise IdP) for paid internet use | **P0 production blocker** — do not treat password demo accounts as production IAM |
| Public TLS edge + Secure cookies + hardened secrets rotation | P0 if exposed beyond LAN |
| Postgres/Redis must remain unpublished; backups encrypted at rest | P0 |
| Marketplace, payments, 3D twin, Radar/Command, mobile, OEM integrations | Out of scope; labeled SIM or unimplemented |

OIDC was **not** implemented. If a customer needs internet-facing paid production, classify OIDC/SSO as a required production control rather than shipping demo passwords.
