# Owner activation checklist — start here

This is the **one place to start** for an internet-facing Mercury Enterprise v16 **pilot**. It is a host-operator procedure. It does **not** claim that DNS, TLS certificates, an IdP tenant, or production secrets exist in git.

| Gate | Status |
| --- | --- |
| LAN / localhost demo | Yes |
| Aviation-company demo on a trusted LAN | Yes (`MERCURY_ENV=development`, host `:3000`) |
| Repository / code readiness for an internet pilot | Yes (Cycles 6–8 + this handoff) |
| Internet-facing pilot | **No** until every **B** step below is done on a real host |
| Paid commercial internet customer | **No** |

**Do not** invent a domain, IdP, certificate, or production secret in this repository. **Do not** paste secrets into git, issues, or chat.

Classification on every item:

- **A.** Cursor can complete automatically in the repository now (templates, scripts, fail-closed checks)
- **B.** Requires accounts, credentials, domains, infrastructure, payment, or decisions from the **owner**
- **C.** Already complete (Cycles 6–8 unless noted)

Related runbooks (do not duplicate here): [ACTIVATION.md](ACTIVATION.md) (A/B/C audit), [OPERATORS.md](OPERATORS.md), [ROLLBACK.md](ROLLBACK.md), [PRODUCTION.md](PRODUCTION.md), [BACKUP.md](../BACKUP.md), [HTTPS.md](../security/HTTPS.md).

Work from the package directory `Mercury_Enterprise_v16/` unless a command says otherwise.

---

## 1. Production domain / DNS

**Class: B** (no domain is registered in this repo). **C:** nginx substitutes `${DOMAIN}`; startup requires `DOMAIN` when `HTTPS_ENABLED=true`.

1. Register or reuse a hostname you control (example shape only: `mercury.your-company.example` — do not copy an invented name into `.env` until DNS is yours).
2. Create DNS **A** (and **AAAA** if you use IPv6) pointing at the VPS public IP from step 2.
3. Wait until `nslookup $DOMAIN` (or your DNS host) returns that IP from the public internet.
4. Put the **hostname only** (no `https://`) in server `.env` as `DOMAIN`.
5. Do **not** point the name at a host that still publishes `:3000`. Use the production overlay (step 12).

**Continue without it?** Yes for LAN. **No** for internet-facing HTTPS / OIDC.

---

## 2. Recommended hosting / VPS architecture and minimum specifications

**Class: B** (you purchase and harden the host). **A/C:** Compose files are the runtime template. Kubernetes is **out of scope**.

**Architecture (pilot):** one well-hardened VPS running Docker Compose.

```
Internet → :80/:443 (host firewall)
         → nginx (Compose profile `production`) TLS 1.2/1.3
              → frontend:80  (Compose network only; :3000 unpublished)
              → backend:8000 (Compose network only; `--workers 2`)
                   → postgres:5432 (Compose network only)
                   → redis:6379    (Compose network only; AOF + noeviction)
         → certbot (ACME webroot + renew loop)
```

Do not publish Postgres, Redis, uvicorn `:8000`, or LAN UI `:3000`.

### Minimum specifications (internet-facing **pilot**)

| Resource | Minimum | Recommended |
| --- | --- | --- |
| vCPU | 2 | 4 |
| RAM | 4 GiB | 8 GiB |
| System disk | 40 GiB SSD | 80 GiB SSD |
| OS | Ubuntu 22.04/24.04 LTS or Debian 12 (x86_64) | Ubuntu 24.04 LTS |
| Docker | Engine 24+ with Compose **plugin** v2 | Current stable from Docker |
| Network | Public IPv4; inbound **80** and **443** | IPv4 + IPv6; SSH only from your admin IP |
| Disk encryption | Required | LUKS / provider volume encryption / BitLocker |

These numbers fit: Postgres 17, Redis 7, two uvicorn workers, frontend nginx, edge nginx, certbot. They are **not** a HA or load-test rating. **Minimum: 2 vCPU, 4 GiB RAM, 40 GiB SSD.** Add RAM before adding backend workers. Do not raise `--workers` without Redis (the production overlay already requires Redis).

**Cursor needs afterward:** confirmation that Compose runs on that host. Still **no** secrets in chat.

**Continue without it?** Yes for LAN.

---

## 3. Ports and firewall

**Class: B** (host firewall / security group). **C:** production overlay unpublishes `:3000`; Postgres/Redis have no host `ports`.

### Required published ports

| Port | Proto | Why |
| --- | --- | --- |
| 80 | TCP | HTTP→HTTPS redirect + Let's Encrypt HTTP-01 |
| 443 | TCP | Public UI + `/api` |
| 22 | TCP | SSH — **restrict to your admin IP** |

### Must stay closed on the public internet

| Port | Service |
| --- | --- |
| 3000 | LAN frontend (unpublished by overlay) |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 8000 | uvicorn |

### Example: Ubuntu `ufw` (**B** — run on the VPS, not in git)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 203.0.113.10 to any port 22 proto tcp comment 'ssh-admin'
sudo ufw allow 80/tcp comment 'http-acme'
sudo ufw allow 443/tcp comment 'https'
sudo ufw enable
sudo ufw status verbose
```

Replace `203.0.113.10` with your real admin IP. If you cannot pin SSH, use key-only SSH and fail2ban; still do not open 3000/5432/6379/8000.

### Example: `nftables` inbound accept set

```
tcp dport { 80, 443 } accept
tcp dport 22 ip saddr 203.0.113.10 accept
```

### Example: cloud security group

Allow inbound **80** and **443** from `0.0.0.0/0` (and `::/0` if IPv6). Allow **22** only from your office/VPN CIDR. No other inbound.

Confirm after overlay up: `ss -lnt` (or `Get-NetTCPConnection` on Windows) must **not** show 3000/5432/6379/8000 on public interfaces.

**Continue without it?** LAN yes. Internet **no**.

---

## 4. HTTPS / TLS certificates

**Class: B** (issue certs on the host). **C:** `deploy/nginx-production.conf.template`, `deploy/init-letsencrypt.sh`, certbot Compose service, TLS 1.2/1.3, HSTS, HTTP→HTTPS.

1. DNS from step 1 must already answer with the VPS IP; ports 80/443 open (step 3).
2. Set in `.env`: `HTTPS_ENABLED=true`, `DOMAIN`, `LETSENCRYPT_EMAIL` (a mailbox you read).
3. From the package directory, bootstrap ACME (**Git Bash / WSL** — the script is `sh`):

```bash
export DOMAIN=your.real.hostname
export LETSENCRYPT_EMAIL=ops@your-company.example
# Optional first pass: STAGING=1
sh deploy/init-letsencrypt.sh
```

The script uses `docker compose -f docker-compose.yml -f docker-compose.production.yml` so `:3000` is not published during bootstrap. Override with `COMPOSE=...` only if you know you need a different file set.

4. Certificates live in Compose volume `certbot_certs` — **never git**. Never commit `privkey.pem`.
5. Staging: `STAGING=1` while debugging ACME rate limits.
6. If a corporate load balancer already terminates TLS: you still set `HTTPS_ENABLED=true` and `DOMAIN`; this repo does not invent that balancer.

**Continue without it?** HTTP LAN yes. Internet-facing pilot **no**.

---

## 5. Production OIDC / IdP

**Class: B** (your IdP tenant). **C:** authorization-code + PKCE, JWKS ID-token verify, Redis state, production URL validation (Cycle 7–8). Auto-provision stays **off**.

Mercury does **not** host an IdP. Use Microsoft Entra ID, Auth0, Okta, or a Keycloak **you** already run.

1. Create a **confidential** client (not a public SPA client).
2. Register this **exact** redirect URI (replace `$DOMAIN` with the hostname from step 1):

```
https://$DOMAIN/api/v1/auth/oidc/callback
```

No `:3000`. No `http://`. No trailing-path invention.

3. Copy from the IdP (into server `.env` only — names in step 11):
   - issuer URL → `MERCURY_OIDC_ISSUER` (must be `https://`, must **not** equal Mercury `DOMAIN` with an empty path)
   - client id → `MERCURY_OIDC_CLIENT_ID`
   - client secret → `MERCURY_OIDC_CLIENT_SECRET`
   - `jwks_uri` from `/.well-known/openid-configuration` → `MERCURY_OIDC_JWKS_URI`
4. Enable **MFA on the IdP**. Mercury does not implement MFA itself.
5. Keep `MERCURY_OIDC_AUTO_PROVISION=false`.
6. Do not insert placeholder issuer/client values “just to boot.” Startup validates URL **shape** and does not contact the IdP.

**Continue without it?** LAN password demo yes. Internet-facing pilot **no**.

---

## 6. PostgreSQL production configuration

**Class: A** Compose service `postgres:17-alpine`. **B:** unique password, disk encryption, optional managed database.

| Setting | Production value |
| --- | --- |
| Image | `postgres:17-alpine` (Compose) |
| Database / user | `mercury` / `mercury` |
| Password | Unique `POSTGRES_PASSWORD` — **not** the LAN default `mercury` |
| URL | `DATABASE_URL=postgresql+psycopg://mercury:<POSTGRES_PASSWORD>@postgres:5432/mercury` (same password) |
| Publish | None (Compose network only) |
| Volume | `mercury_postgres` — never `down -v` on a live host |
| Migrations | Backend entrypoint `alembic upgrade head` |

Optional **B:** a managed Postgres in the same region. Then set `DATABASE_URL` to that instance and do not publish it to the internet. This repo does not provision RDS/Cloud SQL/Azure Database.

Pool knobs (optional): `MERCURY_DB_POOL_SIZE`, `MERCURY_DB_MAX_OVERFLOW`, `MERCURY_DB_POOL_RECYCLE`.

---

## 7. Redis production configuration

**Class: A** Compose `redis:7-alpine` + overlay. **B:** keep it private; size the VPS.

| Setting | Production value |
| --- | --- |
| Image | `redis:7-alpine` |
| Persistence | AOF (`appendonly yes`) |
| Eviction | Overlay: `maxmemory-policy noeviction` (sessions / PKCE / rate limits must not drop) |
| URL | `REDIS_URL=redis://redis:6379/0` (Compose default if unset) |
| Required | Overlay sets `REDIS_REQUIRED=true` |
| Publish | None |
| Volume | `mercury_redis` |

Redis is bound to the Compose network only. Do **not** publish `6379`. Optional Redis `AUTH` is not in this Compose file; do not expose Redis to other hosts without adding AUTH yourself.

Production overlay runs backend `--workers 2` because sessions, PKCE, and application rate limits are Redis-backed.

---

## 8. JWT / cookie / secret generation and storage

**Class: A** empty template + fail-closed startup. **B:** you generate and store values **off git**.

Run these **on your machine or the VPS**, paste into `.env` (or a password manager), and **never commit** `.env`, `backup.key`, or the printed values. Cursor must **not** generate production secrets into the repository.

PowerShell (repeat for each secret):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

OpenSSL (Git Bash / Linux):

```bash
openssl rand -base64 48
```

| Env name | Rule |
| --- | --- |
| `JWT_SECRET` | ≥ 32 characters; not `changeme` / `secret` / `jwt_secret` / `mercury-dev-pepper` |
| `COOKIE_SECRET` | same; generate a **second** independent value |
| `MERCURY_AUTH_PASSWORD` | ≥ 12 characters in production; not `mercury-demo` / `password` / `admin` / `changeme`. Break-glass directory password, not SSO. |
| `POSTGRES_PASSWORD` | unique; keep `DATABASE_URL` in sync |
| Backup key file | optional; see step 9 |

Store `.env` and `backup.key` in a password manager / sealed store. Reverting git does **not** restore secrets. `JWT_SECRET` is **not** a session JWT signer — operator sessions are opaque cookies.

---

## 9. Encrypted off-box backups

**Class: A** `scripts/backup_database.sh` + optional AES-256-CBC. **B:** you choose the off-box destination (this repo does not create a bucket).

On the host (Git Bash), with Compose Postgres unpublished:

```bash
python -c "import secrets; open('backup.key','w').write(secrets.token_urlsafe(48))"
export MERCURY_BACKUP_KEY_FILE=./backup.key
export MERCURY_BACKUP_VIA_COMPOSE=1
export DATABASE_URL=postgresql+psycopg://mercury:YOUR_POSTGRES_PASSWORD@postgres:5432/mercury
export BACKUP_DIR=./backups
sh scripts/backup_database.sh
```

Copy `backups/*.enc` (and `.sha256`) **off the box**. Keep `backup.key` off git and off the same media as the only copy of the ciphertext.

Retention: `MERCURY_BACKUP_RETAIN_DAYS`. Restore: [ROLLBACK.md](ROLLBACK.md) / [BACKUP.md](../BACKUP.md) with `MERCURY_RESTORE_CONFIRM=YES` on a **non-production** copy first.

Host volume encryption (LUKS / provider disk) is the at-rest boundary for `mercury_postgres`. Mercury does not encrypt the Postgres data directory itself.

**Continue without it?** Code/LAN yes. Paid internet **P1** until off-box copies exist.

---

## 10. Named `org_users` and OIDC identity binding

**Class: A** API + [OPERATORS.md](OPERATORS.md). **B:** your people and IdP `sub` values.

Production refuses `MERCURY_SEED_DEMO=true`. Shared `operator` / `viewer` / `reviewer` are **not** internet identities. Keep `MERCURY_OIDC_AUTO_PROVISION=false`.

After the stack is up and you have an admin session:

1. `POST /api/v1/org/users` — named username, unique ≥12-char break-glass password, email.
2. `POST /api/v1/org/users/{username}/oidc` — `oidc_issuer` + `oidc_subject` (`sub` from the IdP token, not always Entra Object ID).
3. `POST /api/v1/memberships` — org/site/role (Operator / Reviewer / Viewer).
4. Confirm an east operator cannot read west resource IDs (403/404).
5. Unprovisioned IdP accounts must receive 403 `Identity is not provisioned for this Mercury tenant`.

---

## 11. Required environment variables (names only)

**Class: A** `.env.example` documents names with empty secrets. **B:** values live only in server `.env`.

Copy `.env.example` → `.env`. Never commit `.env`.

### Must set for internet-facing boot

| Name | Notes |
| --- | --- |
| `DOMAIN` | hostname only |
| `HTTPS_ENABLED` | `true` |
| `LETSENCRYPT_EMAIL` | ACME contact |
| `MERCURY_ENV` | `production` |
| `MERCURY_AUTH_PASSWORD` | ≥12; break-glass |
| `JWT_SECRET` | ≥32; unique |
| `COOKIE_SECRET` | ≥32; unique; different from JWT |
| `POSTGRES_PASSWORD` | unique; matches `DATABASE_URL` |
| `DATABASE_URL` | `postgresql+psycopg://mercury:<password>@postgres:5432/mercury` |
| `REDIS_URL` | `redis://redis:6379/0` (Compose default if empty) |
| `MERCURY_CORS_ORIGINS` | `https://$DOMAIN` (no `*` , no `:3000`) |
| `MERCURY_AUTH_MODE` | `oidc` |
| `MERCURY_REQUIRE_OIDC` | `true` (default when HTTPS is on if unset) |
| `MERCURY_ALLOW_PASSWORD_AUTH` | `false` (break-glass only if you must) |
| `MERCURY_OIDC_ISSUER` | https IdP issuer |
| `MERCURY_OIDC_CLIENT_ID` | confidential client |
| `MERCURY_OIDC_CLIENT_SECRET` | confidential client |
| `MERCURY_OIDC_REDIRECT_URI` | exactly `https://$DOMAIN/api/v1/auth/oidc/callback` |
| `MERCURY_OIDC_JWKS_URI` | https `jwks_uri` from discovery |
| `MERCURY_SEED_DEMO` | `false` |
| `MERCURY_SESSION_COOKIE_SECURE` | `true` (forced when production/HTTPS) |
| `MERCURY_OIDC_AUTO_PROVISION` | `false` |
| `MERCURY_SIM_WORKSPACES` | `false` |

`REDIS_REQUIRED` is set to `true` by `docker-compose.production.yml`; you do not need to set it in `.env`.

### Optional / already defaulted

`MERCURY_OIDC_SCOPES`, `MERCURY_OIDC_USERNAME_CLAIM`, `MERCURY_OIDC_DISCOVERY_URL`, `MERCURY_OIDC_JWKS_CACHE_SECONDS`, `MERCURY_OIDC_CLOCK_SKEW_SECONDS`, `MERCURY_SESSION_COOKIE`, `MERCURY_SESSION_SAMESITE`, `MERCURY_SESSION_TTL_SECONDS`, `MERCURY_RATE_LIMIT_LOGIN_PER_MINUTE`, `MERCURY_RATE_LIMIT_API_PER_MINUTE`, `MERCURY_BACKUP_KEY_FILE`, `MERCURY_BACKUP_RETAIN_DAYS`, `MERCURY_LOG_JSON`, `LOG_LEVEL`, `LOG_FILE`, `MERCURY_DB_POOL_SIZE`, `MERCURY_DB_MAX_OVERFLOW`, `MERCURY_DB_POOL_RECYCLE`, `MERCURY_API_KEY` (avoid on the public internet unless you need machine auth), `MERCURY_FILE_STORAGE_ROOT`, `MERCURY_PUBLICATIONS_STORAGE_ROOT`.

`python scripts/verify_activation.py` checks **names** and, if `.env` exists, reports SET/EMPTY — it **never prints values**. `--strict-internet-env` fails on empty internet-required keys.

---

## 12. Deployment / startup commands

**Class: A** commands below. **B:** run them on the VPS **after** steps 1–8 values exist.

From `Mercury_Enterprise_v16/`:

```powershell
# 1) Confirm overlay (no live IdP required)
python scripts/verify_activation.py
python deploy/validate_deployment.py
docker compose -f docker-compose.yml -f docker-compose.production.yml config

# 2) First certificate (Git Bash / WSL) — after DNS + firewall
# sh deploy/init-letsencrypt.sh

# 3) Internet stack — only 80/443 published
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml up --build -d

# 4) Process status
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml ps
```

LAN demo (not internet) remains:

```powershell
docker compose up --build -d
# UI: http://localhost:3000
```

Do **not** use `docker-compose.dev.yml` (publishes `:8000`) on a customer or internet host.

---

## 13. Health checks and verification commands

**Class: C** probes exist and do not return secrets. **B:** hit the real `https://$DOMAIN` after deploy.

```powershell
curl.exe -fsS https://$DOMAIN/live
curl.exe -fsS https://$DOMAIN/ready
curl.exe -fsS https://$DOMAIN/health
curl.exe -fsSI http://$DOMAIN/
# Expect: Location: https://...

curl.exe -fsS https://$DOMAIN/api/v1/auth/public-config
# Expect oidc_enabled true; no client_secret in the body
```

Compose probes: Postgres `pg_isready`; backend `GET /ready`; frontend/nginx `GET /live`.

Repository-side (no claim that infrastructure is live):

```powershell
python scripts/verify_activation.py
powershell -File scripts/verify_activation.ps1
```

Keep `/metrics` on the Compose network (do not publish it).

SSO smoke (after named users, step 10): open `https://$DOMAIN`, complete IdP login, land in the correct org/site.

---

## 14. Rollback procedure

**Class: C** [ROLLBACK.md](ROLLBACK.md). **B:** you keep previous images/git pins and `.env` off git.

```powershell
# Stop processes, keep volumes
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml stop

# Remove containers, keep named volumes
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml down

# NEVER on a live pilot: docker compose down -v
```

1. Record image ids: `docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml images`.
2. Stop (no `-v`). Check out last known-good git revision **or** retag the previous image.
3. `up --build` / `up -d` with the same two Compose files.
4. Confirm `https://$DOMAIN/live` and `/ready`, then SSO.
5. Data restore: dump first, then `MERCURY_RESTORE_CONFIRM=YES` on a verified archive. Encrypted dumps need the same `MERCURY_BACKUP_KEY_FILE`.

Changing `DOMAIN` or OIDC client settings requires a matching IdP redirect URI before users can sign in.

---

## A / B / C index (this handoff)

| # | Item | Class | Cycle notes |
| --- | --- | --- | --- |
| 1 | Domain / DNS | **B** | — |
| 2 | VPS + min specs | **B** | Compose topology **C** (Cycle 6 overlay) |
| 3 | Firewall 80/443 only | **B** | `:3000` unpublished **C** |
| 4 | Issued TLS certs | **B** | nginx/certbot path **C** |
| 5 | Real OIDC client + exact redirect | **B** | PKCE/JWKS/validation **C** (7–8) |
| 6 | Postgres password + ops | **A** template / **B** ops | **C** image/volume |
| 7 | Redis private + noeviction | **A** overlay / **B** ops | **C** Cycle 8 `noeviction` |
| 8 | Generate secrets off git | **A** template / **B** values | Fail-closed **C** |
| 9 | Off-box `*.enc` copies | **A** scripts / **B** destination | Encryption **C** Cycle 6 |
| 10 | Named users + OIDC bind | **A** API / **B** people | **C** Cycle 8 |
| 11 | Env **names** | **A** `.env.example` | Values **B** |
| 12 | Compose up commands | **A** this doc | Overlay **C** |
| 13 | `/live` `/ready` `/health` + verify script | **C** | Cycle 8 verify script |
| 14 | Rollback runbook | **C** | Cycle 8 `ROLLBACK.md` |
| — | Redis-backed rate limits, `--workers 2` | **C** | Cycle 8 |
| — | Secure / HttpOnly / SameSite cookies | **C** | Cycle 6 |
| — | Email / Marketplace / payments / mobile / Radar / 3D | **C** not in this pilot | Do not enable |

---

## OWNER ACTION REQUIRED (external, in order)

1. Buy or assign a hostname; DNS A/AAAA → VPS.
2. Provision a VPS meeting the **minimum specifications**; enable disk encryption.
3. Firewall: 80/443 (and SSH from admin IP). Close 3000/5432/6379/8000.
4. Copy `.env.example` → `.env` on the host; generate secrets with the commands in step 8; set the names in step 11 from **real** IdP/DNS/cert values.
5. Issue TLS (`sh deploy/init-letsencrypt.sh` then overlay `up`).
6. Create the confidential OIDC client with redirect `https://$DOMAIN/api/v1/auth/oidc/callback`.
7. `docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml up --build -d`
8. Verify `/live` `/ready` `/health` and `public-config`.
9. Create named `org_users`, bind `sub`, grant memberships; disable demo seed.
10. Encrypted backup + **off-box** copy of `*.enc`.

Until those exist, Mercury is a **LAN/localhost** product. The next **code** cycle waits. The next **action** is owner infrastructure.

## What this handoff does not do

- Register a domain, create an IdP app, issue certificates, or purchase a VPS
- Claim Mercury is live on the public internet
- Store production secrets in git
- Enable Marketplace, payments, mobile, 3D visualization, or Radar/Command as production systems
