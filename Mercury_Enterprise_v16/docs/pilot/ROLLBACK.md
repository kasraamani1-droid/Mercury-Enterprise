# Rollback (repository-side runbook)

This is a **host operator** procedure. It does not claim a remote registry or orchestrator exists.

Internet Compose:

```powershell
docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml
```

## Do not destroy data

- `docker compose stop` — processes down, volumes kept
- `docker compose down` — containers removed, **named volumes kept**
- `docker compose down -v` — **destroys** Postgres and Redis data. Never use on a live pilot without a verified restore.

## Application rollback (code)

1. Record the running git revision / image id (`docker compose images`).
2. `docker compose stop` (no `-v`).
3. Check out the last known-good tag/commit on the host, or retag the previous image.
4. Start the same Compose files again (`up --build` or `up -d` with the previous image).
5. Confirm `https://$DOMAIN/live` and `/ready`.
6. Confirm SSO still works (IdP client unchanged).

## Data rollback

1. Take a **new** dump before restoring, even when recovering.
2. Restore the last verified archive:

```powershell
$env:MERCURY_BACKUP_VIA_COMPOSE = "1"
$env:MERCURY_RESTORE_CONFIRM = "YES"
$env:BACKUP_FILE = ".\backups\<verified>.dump"
# Git Bash: sh scripts/restore_database.sh
```

3. Encrypted archives need the same `MERCURY_BACKUP_KEY_FILE`.
4. Hit `/ready`. Do not restore onto the only copy of customer data without an off-box duplicate.

See [BACKUP.md](../BACKUP.md). Off-box copy of `*.enc` is **OWNER ACTION REQUIRED** — this repo does not provision object storage.

## Configuration rollback

- Keep a previous `.env` **off git** (password manager / sealed store).
- Reverting git will **not** restore secrets.
- Changing `DOMAIN` or OIDC client settings requires matching IdP redirect URIs before users can sign in.

## Failed TLS / ACME

- HTTP `:80` must remain reachable for HTTP-01.
- Staging certificates: `STAGING=1` with `deploy/init-letsencrypt.sh`.
- Do not replace Let's Encrypt files with invented certs in git.
