# HTTPS & TLS Termination

Mercury terminates TLS at the edge NGINX service (`nginx` Compose profile: `production`). The frontend container remains HTTP on the internal Docker network; the API is never published on the host in production.

## Requirements

| Control | Behavior |
|---------|----------|
| HTTPS | TLS 1.2 minimum, TLS 1.3 preferred |
| HTTP | `301` redirect to `https://$host$request_uri` |
| Certificates | Let's Encrypt via Certbot webroot |
| Cookies | `HttpOnly`, `Secure`, `SameSite=Lax` (API refuses insecure cookies in production) |
| Headers | HSTS, CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, COOP, CORP |
| Rate limits | `/login`, `/api/v1/auth/login`, and `/api/*` return **429** when exceeded |

## Environment

Copy `.env.example` → `.env` and set:

```env
MERCURY_ENV=production
MERCURY_AUTH_PASSWORD=<unique-12+-char-secret>
JWT_SECRET=<unique-32+-char-secret>
COOKIE_SECRET=<unique-32+-char-secret>
DOMAIN=mercury.example.com
HTTPS_ENABLED=true
LETSENCRYPT_EMAIL=ops@example.com
MERCURY_SESSION_COOKIE_SECURE=true
MERCURY_CORS_ORIGINS=https://mercury.example.com
```

Generate secrets:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

There are **no** insecure defaults for `JWT_SECRET`, `COOKIE_SECRET`, or `MERCURY_AUTH_PASSWORD`. Startup fails closed if they are missing or use forbidden values when `MERCURY_ENV=production` or `HTTPS_ENABLED=true`.

## Deploy (Compose production profile)

From the package root (`Mercury_Enterprise_v16/`):

1. Ensure DNS `A`/`AAAA` for `DOMAIN` points at this host; open ports **80** and **443**.
2. Create `.env` as above.
3. Obtain the first certificate (creates a short-lived dummy cert, starts NGINX, then replaces it with Let's Encrypt):

```bash
export DOMAIN=mercury.example.com
export LETSENCRYPT_EMAIL=ops@example.com
sh deploy/init-letsencrypt.sh
```

Windows (Git Bash / WSL): run the same script. For a staging certificate first, set `STAGING=1`.

4. Start the full stack (production overlay unpublishes `:3000`):

```bash
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml up --build -d
```

5. Verify:

```bash
curl -fsS https://$DOMAIN/live
curl -fsS https://$DOMAIN/ready
curl -fsSI http://$DOMAIN/ | findstr /I Location
# Expect: Location: https://...
```

Sign in at `https://$DOMAIN` via OIDC SSO when `HTTPS_ENABLED=true` (password login is disabled unless break-glass `MERCURY_ALLOW_PASSWORD_AUTH=true`). `:3000` is not the production public endpoint.

## Manual certificate renewal

Certbot renews automatically in the `certbot` service. To renew manually:

```bash
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d "$DOMAIN" \
  --email "$LETSENCRYPT_EMAIL" \
  --agree-tos --no-eff-email --force-renewal
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml exec nginx nginx -s reload
```

## Local HTTP (non-TLS) Compose

Default `docker compose up --build` publishes the frontend proxy on `http://localhost:3000` without the edge `nginx` service. Use this for lab/dev only. Set `MERCURY_ENV=development` and `HTTPS_ENABLED=false` if you need non-Secure cookies over plain HTTP locally.

## Configuration files

| File | Role |
|------|------|
| `deploy/nginx-production.conf` | Static reference config (example hostname) |
| `deploy/nginx-production.conf.template` | Compose envsubst template (`DOMAIN` only via `NGINX_ENVSUBST_FILTER`) |
| `deploy/init-letsencrypt.sh` | First-time certificate bootstrap |
| `deploy/validate_deployment.py` | Offline Compose/NGINX requirement validator (`python deploy/validate_deployment.py`) |
| `frontend/nginx.conf` | Internal UI + `/api` proxy (gzip, WS, timeouts, rate limits, security headers) |
| `docker-compose.yml` | `production` profile for `nginx` + `certbot` |
| `docker-compose.production.yml` | Unpublish `:3000`; require `POSTGRES_PASSWORD`; Redis `noeviction` + `REDIS_REQUIRED`; `--workers 2` |

## Health probes

| Path | Purpose |
|------|---------|
| `GET /live` | Process liveness (JSON) |
| `GET /ready` | Readiness including database (JSON; **503** if not ready) |
| `GET /health` | Structured health summary (JSON) |

Compatibility probes remain at `/api/v1/health` and `/api/v1/ready`.

## Reverse proxy behavior

Edge NGINX proxies:

- `/` → frontend
- `/api/` → backend API (request buffering on, 300s read/send timeout, 25m upload limit)
- `/api/v1/ws` → WebSocket (upgrade headers, long-lived timeouts, buffering off)

## Rollback

```bash
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml down
docker compose up --build -d
```

Confirm `http://localhost:3000/ready` (or `/api/v1/ready`) after rollback.
