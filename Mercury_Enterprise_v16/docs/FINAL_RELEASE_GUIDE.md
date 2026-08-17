# Mercury Enterprise V2.0 Final Release Guide (RC)

## Start
1. Close older Mercury terminal windows, or run `STOP_MERCURY.bat`.
2. Run `CHECK_SYSTEM.bat` once.
3. Run `START_ALL.bat` (or `docker compose up --build`).
4. Open `http://localhost:3000`.
5. API documentation: `http://127.0.0.1:8000/docs`.

## RC verification (smoke)

Automated sequential smoke (API + static UI, no Playwright):

```powershell
cd backend
python -m pytest -q tests/test_rc1_e2e_smoke.py
```

Report: [docs/engineering/RC1_SMOKE_TEST.md](engineering/RC1_SMOKE_TEST.md) (RC1 Blocker 06).

Manual / Compose:

1. `GET /api/v1/health` — status ok/degraded, connectors + advisory flags present.
2. `GET /api/v1/ready` — ready true when DB is up.
3. Sign in → Landing Dashboard KPIs → Aircraft list → Planning → Work Orders → Sign out.
4. Admin/Reviewer audit shows `auth.login` / domain mutations.
5. Executive/History reports load for the selected site.
6. Integrations connector lifecycle remains human-controlled.

## Workspaces
- **Command** — live simulated mission operations + advisory decision explain/review.
- **Digital Twin** — airport asset and trajectory visualization.
- **Radar** — rotating radar scope and contact correlation.
- **Executive** — scoped KPIs, trends, and exports.
- **History** — searchable historical archive and CSV export.
- **Admin** — roles, presence, audit, and health.
- **Integrations / Cloud / Compliance** — connector lifecycle and enterprise surfaces.

## Runbooks
- `docs/runbooks/OPERATOR.md`
- `docs/runbooks/ADMINISTRATOR.md`
- `docs/runbooks/DEPLOY_UPGRADE_ROLLBACK.md`
- `docs/runbooks/DISASTER_RECOVERY.md`

## Important
All targets, aircraft, sensors, evidence, weather, AI assessments, recommendations,
operators, and operational records are simulated demonstration data unless explicitly
replaced with validated adapters. Decision outputs remain advisory. Human operators
remain in full control.
