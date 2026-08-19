# Commercial production runbook (Cycle 6)

This is **not** a TC / FAA / EASA certification claim. Mercury remains an MRO/AMO operations platform. Workforce flags, Command/Radar/3D airport twin, and SIM labels are not operational authorities.

## What Cycle 6 actually enables

| Gate | Status after this cycle |
| --- | --- |
| Controlled LAN / localhost customer pilot | Yes, with named operators and `MERCURY_ENV=development` on `:3000` |
| Internet-facing beta | Only after you complete the **external** steps below (DNS, real TLS certs, real IdP) |
| Paid internet production | Blocked until a real IdP is configured, backups are encrypted/off-box, and named identities replace shared demo users |

`:3000` is the LAN UI. It is **not** the production public endpoint. Production public traffic must terminate on nginx `:443` using `docker-compose.production.yml` (frontend `:3000` unpublished).

## Prerequisites

- Docker Compose
- A local `.env` copied from `.env.example` — never commit it
- Generated secrets: `JWT_SECRET`, `COOKIE_SECRET`, `MERCURY_AUTH_PASSWORD` (≥ 12 characters, not a demo word)
- Production: `MERCURY_SEED_DEMO=false` (startup refuses demo seed)
- Internet / HTTPS: real DNS `DOMAIN`, `HTTPS_ENABLED=true`, `LETSENCRYPT_EMAIL`, **OIDC client issued by your IdP**

## Authentication

### LAN / controlled pilot (password)

```
MERCURY_ENV=development
MERCURY_SESSION_COOKIE_SECURE=false
MERCURY_AUTH_MODE=password
MERCURY_SEED_DEMO=true
```

Demo users `operator` / `viewer` / `reviewer` share `MERCURY_AUTH_PASSWORD`. They are **not** production identities.

### Internet TLS (OIDC required)

HTTPS enables `MERCURY_REQUIRE_OIDC` by default. Startup **fails closed** unless all of these are set from your IdP (Azure AD / Okta / any OIDC provider):

- `MERCURY_AUTH_MODE=oidc`
- `MERCURY_OIDC_ISSUER`
- `MERCURY_OIDC_CLIENT_ID`
- `MERCURY_OIDC_CLIENT_SECRET`
- `MERCURY_OIDC_REDIRECT_URI` (must be `https://$DOMAIN/api/v1/auth/oidc/callback`)

Do **not** paste placeholder client secrets into `.env` “just to boot.”

Password login is disabled when OIDC is required unless you explicitly set `MERCURY_ALLOW_PASSWORD_AUTH=true` (break-glass only; not a paid-internet control).

Directory mapping: OIDC `sub` + issuer, then email, then `preferred_username`. Unknown identities are **rejected** (`MERCURY_OIDC_AUTO_PROVISION` defaults false). Provision users in Mercury (admin directory) before first SSO login.

Remaining IdP work you must do outside this repository:

1. Create a confidential OIDC client
2. Allow redirect `https://YOUR_DOMAIN/api/v1/auth/oidc/callback`
3. Issue client id/secret into the server `.env` only
4. Optionally enable MFA on the IdP — Mercury does not implement MFA itself
5. Keep the backend at **one uvicorn worker** (Compose default). PKCE `state` is in-process memory, not Redis
6. ID-token JWT signature verification via JWKS is **not** implemented — identity is taken from TLS userinfo to the configured issuer

## TLS / internet exposure

```powershell
# From the package directory. Unpublishes :3000. Public ports are 80/443 only.
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml up --build
```

- HTTP on :80 redirects to HTTPS except ACME and `/live`/`/ready`/`/health`
- Session cookies are `HttpOnly`, `SameSite=Lax`, `Secure`
- Postgres and Redis stay unpublished
- Set `POSTGRES_PASSWORD` to a unique value and keep `DATABASE_URL` in sync
- CORS must be `https://YOUR_DOMAIN` — wildcards and `:3000` are refused for HTTPS

Certificates: Let's Encrypt volume `certbot_certs`. See `deploy/certs/README.md`. Never commit private keys.

## Backup / restore

See [BACKUP.md](../BACKUP.md).

- Timestamped dumps + SHA-256
- Optional encryption: `MERCURY_BACKUP_KEY_FILE` (openssl AES-256-CBC)
- Retention: `MERCURY_BACKUP_RETAIN_DAYS`
- Destructive restore requires `MERCURY_RESTORE_CONFIRM=YES`
- Off-box copy of encrypted dumps is the customer’s object-storage / tape / provider boundary
- Host/volume encryption (BitLocker, LUKS, cloud disk encryption) covers Postgres volumes at rest

## Admin / tenant setup

1. Create the organization and sites in Organization Portal
2. Create **named** `org_users` (not shared demo logins)
3. Assign memberships per organization
4. Bind OIDC subjects on first successful SSO (or pre-set `oidc_issuer` / `oidc_subject` via directory)
5. Confirm east-operator cannot read west resource IDs (403/404)

## SIM limits

When `MERCURY_ENV=production`, Command Ops, Radar Console, Ops Twin (3D airport), and Cloud & HA workspaces are **hidden**. They remain in the codebase for LAN demos with `MERCURY_SIM_WORKSPACES=true`. They are not operational ATC/radar/3D systems.

Workforce `license_ok` / `authorization_ok` are planner-entered flags, not a certification determination.

## Health

```powershell
curl.exe https://YOUR_DOMAIN/live
curl.exe https://YOUR_DOMAIN/ready
curl.exe https://YOUR_DOMAIN/health
```

Probes do not return passwords, tokens, or secrets. `/metrics` should stay on the Compose network.

## Rollback

1. `MERCURY_RESTORE_CONFIRM=YES` restore of the last verified dump
2. `docker compose stop` (do not `down -v` unless you intend to destroy Postgres)
3. Redeploy the previous image tag / git revision
4. Confirm `/ready`

## Data handling

- Do not commit `.env`, `*.db`, dumps, `data/`, certs, or backup keys
- Audit events record login, logout, authz denials, and domain mutations — never session cookies or Authorization headers
- Customer data leaves the host only via operator-controlled encrypted backups
