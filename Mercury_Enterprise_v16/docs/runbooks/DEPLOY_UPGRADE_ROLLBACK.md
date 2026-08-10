# Deploy, Upgrade, and Rollback — Mercury Enterprise V2.0

## Local reference deploy

1. Configure `.env` (database URL, auth password, CORS, cookie secure flag).
2. `docker compose up --build`
3. Verify `GET /api/v1/ready` and UI at port 3000.

## Upgrade

1. Put operators in awareness of brief restart.
2. Backup database volume / SQLite file (see Disaster Recovery runbook).
3. Pull/build new images or update working tree to the release tag.
4. Restart backend/frontend.
5. Run smoke: health, ready, login, dashboard, decision evaluate/review, reports, connectors, audit.

## Rollback

1. Redeploy previous known-good tag/commit (Milestone checkpoints: `checkpoint-milestone-2-pre`, `c741e7f`).
2. Restore DB backup only if schema/data corruption occurred (Milestone 2 default has no new tables).
3. Do **not** delete `audit_events` to “fix” application bugs.
4. Confirm `/ready` and Command login after rollback.

## Compatibility notes

- Milestone 2 APIs are additive (`/decisions*`, enriched health).
- Older frontends ignore unknown JSON keys.
- In-memory decision reviews are lost on restart (Option A); audit rows remain.
