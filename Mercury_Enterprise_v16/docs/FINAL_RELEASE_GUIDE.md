# Mercury Enterprise V2.0 Final Release Guide (RC)

## Start
1. Close older Mercury terminal windows, or run `STOP_MERCURY.bat`.
2. Run `CHECK_SYSTEM.bat` once.
3. Run `START_ALL.bat` (or `docker compose up --build`).
4. Open `http://localhost:3000`.
5. API documentation: `http://127.0.0.1:8000/docs`.

## RC verification (smoke)
1. `GET /api/v1/health` — status ok/degraded, connectors + advisory flags present.
2. `GET /api/v1/ready` — ready true when DB is up.
3. Login as Operator → Command Decision Timeline → Evaluate → Review.
4. Admin audit shows `decision.evaluate` / `decision.review`.
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
