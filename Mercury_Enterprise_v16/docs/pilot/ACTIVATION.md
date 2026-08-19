# Internet-facing activation checklist (Cycle 8)

**Start here for the sequential owner procedure:** [OWNER_HANDOFF.md](OWNER_HANDOFF.md) (VPS minimum specs, secret-generation commands, firewall examples, exact env names, compose/health/rollback commands). This file remains the **A/B/C audit**. Do not treat the two as competing checklists.

This document is the **pre-activation audit** for Mercury Enterprise v16. It distinguishes **repository / code readiness** from **deployed infrastructure readiness**.

Mercury is **not** internet-facing until the owner completes every **B** item. This repository does **not** contain a real domain, IdP tenant, issued TLS certificate, or production secret. Cursor will not invent those values.

| Gate | Status after Cycle 8 (repo-side) |
| --- | --- |
| LAN / localhost demo | Yes |
| Aviation-company demo on a trusted LAN | Yes |
| Controlled customer pilot on a trusted LAN | Yes (`MERCURY_ENV=development`, `:3000`) |
| Internet-facing pilot | **No** — OWNER ACTION REQUIRED (DNS, TLS certs, real IdP) |
| Paid production customer | **No** |

Do **not** simulate external infrastructure. Do **not** paste placeholder IdP credentials into `.env` “just to boot.”

Classification used below:

- **A.** Cursor can implement or configure **in this repository**
- **B.** Requires owner / external account action
- **C.** Already complete (Cycles 6–7 unless noted)

## Checklist

| Item | Class | Notes |
| --- | --- | --- |
| Production domain / DNS `A`/`AAAA` for `$DOMAIN` | **B** | No domain is registered in this repo. Set `DOMAIN` in `.env` only after DNS exists. |
| Hosting / runtime (public IP, VPS or equivalent) | **B** | Compose files are templates. Nothing is deployed. **Min specs** (pilot): 2 vCPU / 4 GiB RAM / 40 GiB SSD; recommended 4 / 8 / 80. See [OWNER_HANDOFF.md](OWNER_HANDOFF.md) §2. |
| HTTPS / TLS certificates (Let's Encrypt or equivalent) | **B** | nginx + certbot **path** exists (`deploy/`, `docs/security/HTTPS.md`). No issued certs in git. |
| ACME / certbot Compose service | **C** | Profile `production` in `docker-compose.yml` |
| nginx TLS 1.2/1.3, HSTS, CSP, HTTP→HTTPS | **C** | `deploy/nginx-production.conf` + `.template` |
| Unpublish `:3000` on internet overlay | **C** | `docker-compose.production.yml` `ports: !reset []` |
| OIDC IdP tenant (Entra ID / Auth0 / Keycloak / Okta) | **B** | Code-complete; **not activated**. No live tenant. |
| OIDC confidential client (id + secret) | **B** | Leave `MERCURY_OIDC_*` empty until issued. |
| Redirect / callback URL on the IdP | **B** | Must be `https://$DOMAIN/api/v1/auth/oidc/callback` |
| OIDC code: PKCE, JWKS verify, Redis state | **C** | Cycle 7 |
| Production OIDC **validation** (issuer https, client id, redirect matches `DOMAIN`, `jwks_uri`) | **A** → **C** (Cycle 8) | Fail-closed at startup. Does not contact the IdP. |
| Production PostgreSQL | **A** templates / **B** operations | Compose `postgres` service. Owner sets `POSTGRES_PASSWORD` and keeps `DATABASE_URL` in sync. No managed cloud DB is provisioned here. |
| Production Redis | **A** templates / **B** operations | Compose `redis`, overlay `REDIS_REQUIRED=true`, `noeviction`. Unpublished. |
| Secrets / env vars (`.env` from `.env.example`) | **A** template / **B** values | Never commit `.env`. Owner generates with `python -c "import secrets; print(secrets.token_urlsafe(48))"` or `openssl rand -base64 48` — commands in [OWNER_HANDOFF.md](OWNER_HANDOFF.md) §8. Cursor does not generate or commit values. |
| Encryption / key requirements | **A** docs+scripts / **B** keys | `JWT_SECRET` / `COOKIE_SECRET` ≥ 32 chars; optional `MERCURY_BACKUP_KEY_FILE`; host volume encryption is the owner's disk. |
| Off-box encrypted backups | **A** tooling / **B** copy destination | Scripts encrypt dumps. **No** cloud bucket is invented. Owner copies `*.enc` off the host. |
| Email / notification | **C** not required for SSO | Mercury login does not send mail. Connect catalog lists SMTP as a **future** connector, not a production mailer. Optional later (**B** if you want mail). |
| Health checks `/live` `/ready` `/health` | **C** | Do not return secrets. Overlay healthchecks probe `/ready`. |
| Logging / audit | **C** + Cycle 8 redact | JSON logs redact secrets; audit details are redacted; login/logout do not store cookies. |
| Firewall / network | **B** | Owner opens 80/443 only; do not publish Postgres, Redis, or `:3000`. `ufw` / nftables / security-group examples: [OWNER_HANDOFF.md](OWNER_HANDOFF.md) §3. |
| Persistent storage | **C** volumes | `mercury_postgres`, `mercury_redis`, `certbot_*`. Owner must not `down -v` on a live host. |
| Deployment / rollback | **A** docs + verify script (Cycle 8) | See [ROLLBACK.md](ROLLBACK.md). Image/git pin is the owner's registry choice (**B** if using a remote registry). |
| Redis-backed rate limits (multi-worker) | **A** → **C** (Cycle 8) | Application limiter uses Redis when `REDIS_URL` is attached / required. nginx edge limits remain. |
| Named `org_users` bound to IdP `sub` | **A** API + docs / **B** people | `POST /api/v1/org/users` and `POST /api/v1/org/users/{username}/oidc`. Auto-provision stays **off**. |
| Session cookies Secure / HttpOnly / SameSite | **C** | Forced Secure when production or HTTPS. |
| Proxy / `X-Forwarded-*` | **C** | nginx sets headers; FastAPI `ProxyHeadersMiddleware` when HTTPS + `DOMAIN`. |
| Activation verification (compose + env names, no secret print) | **A** → **C** (Cycle 8) | `python scripts/verify_activation.py` |

## OWNER ACTION REQUIRED (external)

Complete these **in order**. Development on LAN can continue without them. **Internet-facing activation cannot.**

### 1. Public hostname and DNS

1. **Service:** DNS zone + hostname (registrar / DNS host).
2. **Why:** TLS certificates and OIDC redirect URLs are bound to a real hostname. Mercury will not invent `DOMAIN`.
3. **Options:** Any registrar (Cloudflare DNS, Route 53, Azure DNS, your existing corporate zone).
4. **What to put in `.env` after it exists:** `DOMAIN` (hostname only, no `https://`).
5. **Where:** `.env` (never git); nginx substitutes `${DOMAIN}` from Compose.
6. **Precautions:** Do not point the name at a host that still publishes `:3000`. Use the production overlay so only 80/443 are published.
7. **Continue without it?** Yes for LAN. **No** for internet-facing HTTPS.

### 2. Host with a public IPv4 (and IPv6 if used)

1. **Service:** VPS / VM with a public IP (or a reverse proxy you already operate).
2. **Why:** Let's Encrypt HTTP-01 and user browsers must reach ports 80 and 443.
3. **Options:** A single well-hardened VPS is enough for a pilot. Kubernetes is **out of scope**. Minimum: **2 vCPU, 4 GiB RAM, 40 GiB SSD**, Ubuntu 22.04/24.04 or Debian 12, Docker Engine 24+ / Compose v2, public IPv4, disk encryption. Recommended: **4 vCPU, 8 GiB RAM, 80 GiB SSD**. Full table: [OWNER_HANDOFF.md](OWNER_HANDOFF.md) §2.
4. **What Cursor needs afterward:** confirmation that Compose runs on that host; still **no** secrets in chat.
5. **Where:** operator host, not this git repo.
6. **Precautions:** Firewall allow 80/443 only. Postgres and Redis stay on the Compose network. Disk encryption (BitLocker/LUKS/cloud volume).
7. **Continue without it?** Yes for LAN.

### 3. Issued TLS certificates

1. **Service:** Let's Encrypt (via existing `certbot` service) or your corporate PKI.
2. **Why:** HTTPS is mandatory for internet OIDC and Secure cookies.
3. **Options:** Let's Encrypt (script `deploy/init-letsencrypt.sh`); commercial CA; existing load-balancer certs (then you terminate TLS in front and must still set `HTTPS_ENABLED=true`).
4. **Env after issue:** `HTTPS_ENABLED=true`, `LETSENCRYPT_EMAIL`, `DOMAIN`.
5. **Where:** `.env`; certificates in Compose volume `certbot_certs` — **never git**.
6. **Precautions:** Never commit `privkey.pem`. Staging first (`STAGING=1`) if you are debugging ACME.
7. **Continue without it?** Yes for HTTP LAN. **No** for internet-facing pilot.

### 4. Real OIDC identity provider and confidential client

1. **Service:** Microsoft Entra ID, Auth0, Okta, or self-hosted Keycloak (your IdP).
2. **Why:** Internet TLS enables `MERCURY_REQUIRE_OIDC`. Password demo users are not production identities. JWKS verification needs the IdP's real `jwks_uri`.
3. **Options:** Entra ID (Azure AD) for Microsoft shops; Auth0/Okta for SaaS IdP; Keycloak if you already run it. Mercury does not host an IdP.
4. **Env Cursor will use (values come from the IdP — do not invent them):**
   - `MERCURY_AUTH_MODE=oidc`
   - `MERCURY_REQUIRE_OIDC=true`
   - `MERCURY_ALLOW_PASSWORD_AUTH=false` (break-glass only if you must)
   - `MERCURY_OIDC_ISSUER`
   - `MERCURY_OIDC_CLIENT_ID`
   - `MERCURY_OIDC_CLIENT_SECRET`
   - `MERCURY_OIDC_REDIRECT_URI` = `https://$DOMAIN/api/v1/auth/oidc/callback`
   - `MERCURY_OIDC_JWKS_URI` (copy from `/.well-known/openid-configuration`)
   - optional `MERCURY_OIDC_DISCOVERY_URL` if it is not `{issuer}/.well-known/openid-configuration`
   - `MERCURY_CORS_ORIGINS=https://$DOMAIN`
5. **Where:** server `.env` only. IdP admin console must allow that exact redirect URI.
6. **Precautions:** Confidential client (not a public SPA client). Enable MFA **on the IdP**. Keep `MERCURY_OIDC_AUTO_PROVISION=false`. Do not paste secrets into issues, chat, or git. Rotate the client secret if it leaks.
7. **Continue without it?** Yes for LAN password demo. **No** for internet-facing pilot. Do not substitute a fake issuer.

### 5. Production database password and Redis

1. **Service:** Compose Postgres + Redis on the host (already defined). Optional: a managed Postgres you wire via `DATABASE_URL` (**B** if you choose a cloud DB).
2. **Why:** System of record + shared sessions/PKCE/rate limits across `--workers 2`.
3. **Options:** Keep Compose Postgres on encrypted disks, or a managed Postgres in the same region. Redis should stay private (no public 6379).
4. **Env:** `POSTGRES_PASSWORD`, `DATABASE_URL` (same password), `REDIS_URL=redis://redis:6379/0` (Compose). Overlay sets `REDIS_REQUIRED=true`.
5. **Where:** `.env` + `docker-compose.production.yml`.
6. **Precautions:** Unique `POSTGRES_PASSWORD` (not `mercury`). Never publish 5432/6379. Unique `JWT_SECRET` / `COOKIE_SECRET`.
7. **Continue without it?** LAN Compose can keep the documented LAN password. **Internet hosts must not.**

### 6. Off-box encrypted backup copies

1. **Service:** Object storage, offline disk, or your existing backup product — **you** choose. This repo does not create a bucket.
2. **Why:** Compose volumes are not off-site recovery.
3. **Options:** Encrypted USB/NAS; provider snapshot of the encrypted volume; object storage you already have.
4. **What Mercury needs:** nothing in git. Locally: `MERCURY_BACKUP_KEY_FILE`, then copy `backups/*.enc` off the box.
5. **Where:** host filesystem + your off-box target. See [BACKUP.md](../BACKUP.md).
6. **Precautions:** Key file never in git. Test restore with `MERCURY_RESTORE_CONFIRM=YES` on a **non-production** copy.
7. **Continue without it?** Code and LAN yes. Paid internet **P1** until copies exist.

### 7. Named operators

1. **Service:** Your staff identities in the IdP + Mercury directory.
2. **Why:** Shared `operator`/`viewer`/`reviewer` demo users are refused in production seed and are not accountable.
3. **Options:** Pre-create `org_users` (see [OPERATORS.md](OPERATORS.md)) and bind `oidc_issuer` + `oidc_subject`.
4. **API:** `POST /api/v1/org/users`, `POST /api/v1/org/users/{username}/oidc`, memberships.
5. **Where:** running API after deploy — not in this git repo.
6. **Precautions:** Least privilege. Confirm east/west tenant isolation. Disable demo seed (`MERCURY_SEED_DEMO=false`).
7. **Continue without it?** LAN demo yes. Internet pilot **no** for accountable access.

### 8. Firewall and exposing only 80/443

1. **Service:** Host firewall / security group.
2. **Why:** Default LAN Compose publishes `:3000`, which is **not** the public endpoint.
3. **Options:** nftables, ufw, cloud security groups.
4. **Config:** `docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml`
5. **Where:** host, not git.
6. **Precautions:** Do not port-forward Postgres, Redis, uvicorn `:8000`, or `:3000`. Example `ufw`: allow 80/443 and SSH from your admin IP only — [OWNER_HANDOFF.md](OWNER_HANDOFF.md) §3.
7. **Continue without it?** LAN yes.

## Repository commands (no live IdP required)

From `Mercury_Enterprise_v16/`. Exact compose, health, and secret-generation commands: [OWNER_HANDOFF.md](OWNER_HANDOFF.md) §§8, 11–13.

```powershell
python scripts/verify_activation.py
docker compose -f docker-compose.yml -f docker-compose.production.yml config
```

`verify_activation.py` checks that required **names** are documented and, if `.env` exists, that they are **set** — it never prints secret values.

Internet start (only after B items exist):

```powershell
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml up --build -d
```

## What this cycle did **not** do

- Register a domain, create an IdP app, or issue certificates
- Claim Mercury is live on the public internet
- Store production secrets in git
- Enable Marketplace, payments, mobile, 3D viz, or Radar/Command as production systems
