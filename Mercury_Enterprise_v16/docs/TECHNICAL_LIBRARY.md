# Technical Library

Browse path:

```
Manufacturer → Aircraft Family → Aircraft Model → Publication Type → ATA Chapter → Publication → Revision
         ↘ Task → Component → Serialized Component → Maintenance History / Technical Log
```

Browse: `GET /api/v1/library/browse` (supports `family_id`). Search: `GET /api/v1/library/search`.

The Technical Library desk walks that path in the vanilla JS UI (`library.js` + `publications-ops.js`). OEM binaries are never uploaded; create forms store locators only.

Catalog includes AMM, CMM, IPC/AIPC, WDM, SDM, FIM, MFIM, TSM, SB, EO, ARM, GHSI (ground handling), ATA-AMM/ATA-SPM, CDL, MEL/DDG, MPD, WBM (weight & balance), SRM, NDT, SPM (standard practices), and related flight/engineering types.

Also related: Service Bulletins · Engineering Orders · Fault Codes · Technical Logbook entries.

## Integration

| Link | Purpose |
|------|---------|
| ATA chapter | Primary + multi ATA associations |
| Component catalog / alternates | CMM/IPC applicability + interchangeability |
| Aircraft family / model / variant | Type design applicability |
| Fleet aircraft | Resolve model → publications |
| Maintenance tasks | Full task engine binds publication + revision; release writes tech log ([MAINTENANCE_TASKS.md](MAINTENANCE_TASKS.md)) |
| Fault codes | Defect ↔ ATA ↔ task graph |
| AI stubs | Index / embedding / cross-ref placeholders (no AI compute) |

## Search / filter

`/api/v1/library/search` and `/api/v1/publications` — code, title, model, manufacturer, ATA, revision, dates, free-text `q`.

## License-safe storage

Abstraction: `backend/app/publications/storage.py` — locators only. Organizations must hold OEM licensing before indexing or hosting protected manuals.

## Related

[PUBLICATIONS.md](PUBLICATIONS.md) · [AIRCRAFT_CONFIGURATION.md](AIRCRAFT_CONFIGURATION.md) · [TECHNICAL_LOGBOOK.md](TECHNICAL_LOGBOOK.md)
