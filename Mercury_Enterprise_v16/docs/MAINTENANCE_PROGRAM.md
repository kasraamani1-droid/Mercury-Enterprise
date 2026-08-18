# Maintenance Programs

Revision-controlled aircraft maintenance programs (operator / manufacturer).

## Model

- **Program** header: code, title, manufacturer, family, model, operator, status  
- **Revisions**: immutable rows — activate supersedes prior revision (never overwrite)

Statuses: `draft` | `active` | `superseded` | `archived` · soft-delete via `deleted_at`

## APIs

| Method | Path | Permission |
|--------|------|------------|
| GET/POST | `/api/v1/planning/programs` | `planning.read` / `planning.manage` |
| GET/POST | `/api/v1/planning/programs/{id}/revisions` | read / manage |

## Related

[MPD.md](MPD.md) · [FORECAST_ENGINE.md](FORECAST_ENGINE.md) · [PLANNING_DASHBOARD.md](PLANNING_DASHBOARD.md)
