# Contributing

## Principles

- Prefer **additive** changes; do not redesign architecture or replace vanilla JS / FastAPI.
- Do not introduce React, Vue, Angular, Next.js, or other SPA frameworks.
- No placeholders, fake APIs, or mocked production logic unless explicitly requested.
- Keep commits focused; do not commit `.env` or secrets.

## Branching

1. Branch from `main`: `feature/<short-name>` or `docs/<short-name>`.
2. Keep PRs small and reviewable.
3. Base PRs on `main`.

## Development setup

Follow [INSTALL.md](INSTALL.md). For API work:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pytest tests/ -q
```

## Coding expectations

| Layer | Expectation |
|-------|-------------|
| Backend | FastAPI routers/services; reuse `audit`, `health`, `metrics`, RBAC helpers |
| Frontend | Vanilla JS modules under `frontend/js/`; preserve layout and routing |
| Config | Document new env vars in `.env.example` with no insecure defaults |
| Docs | Update the relevant guide in this documentation set |

## Tests

- All existing backend tests must pass.
- Add tests for new API behavior (authz, audit, health, metrics).
- Do not weaken production security defaults to make tests pass; use `conftest` env overrides.

## Pull requests

Include:

1. Short summary of why the change exists  
2. Test plan (commands run + manual checks)  
3. Notes on API/UI/env changes and residual risks  

Draft PRs are welcome for early review.

## Security contributions

Report sensitive issues privately to the repository maintainers. Do not file public issues that include credentials, exploit PoCs against production systems, or customer data.
