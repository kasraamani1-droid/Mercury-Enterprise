# Closed-loop pilot demo (C-GMEA) — SIM / demo

This walk uses seeded **Aviation East** data. Label the session as **SIM / demo**. Do not present Radar, Command, 3D airport twin, reliability/MTBUR/MTBF, or workforce flags as production certification.

Aircraft: `ac-c-gmea` / registration **C-GMEA**. Work package: `WP-DEMO-001` (`wp-demo-c-gmea`). Reset by restoring a dump or restarting with idempotent seed (seed does not wipe operator-created rows).

## Roles

| Role | Login user | What to show |
| --- | --- | --- |
| Maintenance Controller / Planner | `operator` | Planning desk, generate WP, hangar, workforce assign |
| AME / Technician | `operator` | Work order / job card execution (demo AME E-1001) |
| Logistics / Stores | `operator` | Logistics desk, material request on the job card |
| Quality / Supervisor | `reviewer` | Inspect / ACA paths; planning read; cannot manage planning |
| Read-only | `viewer` | Lists and objects; mutations return 403 |

## Script (about 15 minutes)

1. Sign in as `operator`. Open **Home**, then aircraft **C-GMEA**.
2. **Configuration / Components** — installed configuration on existing component APIs.
3. **Publications** tab — library locators for this aircraft (`GET /publications/by-aircraft/ac-c-gmea`).
4. **Planning** — due/forecast, A-check `A-CHK-C-GMEA`, deferred defect DD-1001, hangar, **workforce plan** on `WP-DEMO-001` (E-1001 technician, E-2001 ACA, E-3001 II). Flags are planner-entered.
5. Optionally generate a work package from a **due** check that has no package yet (409 if already generated).
6. Open work order **WO-DEMO-7100** — job cards, materials, workforce lines on the package.
7. **Personnel** — E-1001 qualifications (technician is not ACA).
8. **Logistics** — stock/tools for the visit; scan lookup is identifier search, not a hardware scanner.
9. **Digital Twin** (aircraft object tab) — history/passport if a twin is linked. Not the 3D airport SIM page.
10. Sign in as `viewer` — same lists, no assign/generate. Sign in as `reviewer` — inspect/release, no planning create.

## Automated companion

`backend/tests/test_pilot_closed_loop.py` walks the same API sequence without a browser.

## Reset

Restore a Compose dump ([DEPLOY.md](DEPLOY.md)) or recreate a local sqlite test database. Do not treat `MERCURY_SEED_DEMO` as a wipe of operator data.
