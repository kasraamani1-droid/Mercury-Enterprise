# Mercury Enterprise v16 — Task 2

This package upgrades the existing Mercury v15/v16 working copy with:

- Version identifiers changed to 16.0.0
- Connector SDK and registry
- Mock flight-data connector
- Mock weather connector
- Normalized observation model
- In-memory event bus
- Connector REST endpoints
- Connector tests

## Apply

1. Stop Mercury with `STOP_MERCURY.bat`.
2. Back up the working project.
3. Copy everything in this package into the inner project folder that contains `START_ALL.bat`.
4. Allow Windows to merge folders and replace matching files.
5. Run:

```powershell
.\CHECK_SYSTEM.bat
.\START_ALL.bat
```

## Verify

- UI: http://localhost:3000
- Health: http://127.0.0.1:8000/api/v1/health
- Connector catalog: http://127.0.0.1:8000/api/v1/connectors
- Events: http://127.0.0.1:8000/api/v1/events
- API docs: http://127.0.0.1:8000/docs
