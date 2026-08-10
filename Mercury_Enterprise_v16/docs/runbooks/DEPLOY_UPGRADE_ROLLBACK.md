# Deploy, Upgrade, and Rollback — Mercury Enterprise V2.0

## Local reference deploy

1. Copy `.env.example` to `.env` and set secrets (`MERCURY_AUTH_PASSWORD`, `DATABASE_URL`, CORS, cookie secure flag).
2. For Postgres schema: from `backend/`, run `alembic upgrade head` (or rely on `create_all` only for disposable empty DBs).
3. `docker compose up --build`
4. Verify `GET http://localhost:3000/api/v1/ready` (via NGINX) and UI sign-in at port 3000.
5. Backend remains on the Compose network (`expose: 8000`); UI must use same-origin `/api` (default frontend config).

## Upgrade

1. Put operators in awareness of brief restart.
2. Backup database volume / SQLite file (see Disaster Recovery runbook).
3. Pull/build new images or update working tree to the release tag.
4. Run `alembic upgrade head` against Postgres when migrations exist.
5. Restart backend/frontend (backend must stay **single worker** until shared sessions exist).
6. Run smoke: health, ready, login, dashboard, decision evaluate/review, reports, connectors, audit; confirm anonymous incident/ops writes fail.

## Rollback

1. Redeploy previous known-good tag/commit (Milestone checkpoints: `checkpoint-milestone-2-pre`, `c741e7f`).
2. Restore DB backup only if schema/data corruption occurred; use `alembic downgrade` only when a safe downgrade path exists.
3. Do **not** delete `audit_events` to “fix” application bugs.
4. Confirm `/ready` and Command login after rollback.

## Compatibility notes

- Milestone 2 APIs are additive (`/decisions*`, enriched health).
- Production hardening requires authentication on previously open reads (incidents, alerts, dashboard, platform, ops); anonymous clients must login.
- Older frontends ignore unknown JSON keys.
- In-memory decision reviews are lost on restart (Option A); audit rows remain.
- Frontend API default is relative `/api/v1`; local dual-process demos use `config.local.js`.
