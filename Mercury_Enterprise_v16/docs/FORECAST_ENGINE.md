# Forecast & Due List Engine

Computes upcoming maintenance from checks, ADs, SBs, EOs, and deferred defects using calendar, flight hours, and flight cycles.

## Urgency

| Bucket | Meaning |
|--------|---------|
| `overdue` | Past due date or negative remaining FH/FC |
| `due_soon` | Within horizon (default 30 days for soon bucket) |
| `future` | Within selected forecast horizon |

Horizons: 30 / 90 / 180 / 365 days (API accepts 1–3650).

## APIs

| Method | Path |
|--------|------|
| GET | `/api/v1/planning/forecast?horizon_days=` |
| GET | `/api/v1/planning/due-list` |

Due list merges buckets sorted by urgency.

## Related

[PLANNING_DASHBOARD.md](PLANNING_DASHBOARD.md) · [AIRCRAFT_STATUS.md](AIRCRAFT_STATUS.md)
