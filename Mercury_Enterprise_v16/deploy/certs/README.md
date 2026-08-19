# Certificate material for the production TLS edge.

Let's Encrypt certificates live in the Compose volume `certbot_certs`, not in git.

Never commit:

- `privkey.pem`
- `fullchain.pem`
- `*.key`
- operator-generated self-signed certs used for staging

Production start (after DNS for `$DOMAIN` points at this host):

1. Copy `.env.example` to `.env` and generate secrets.
2. Set `HTTPS_ENABLED=true`, `DOMAIN`, `LETSENCRYPT_EMAIL`.
3. Configure OIDC (`MERCURY_OIDC_*`) — required when HTTPS is enabled.
4. `sh deploy/init-letsencrypt.sh` (or equivalent ACME bootstrap).
5. `docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml up --build`

Host-level disk encryption / cloud volume encryption is the off-box encryption-at-rest boundary for Postgres volumes. Backup archives can be encrypted with `MERCURY_BACKUP_KEY_FILE` (see `docs/BACKUP.md`).
