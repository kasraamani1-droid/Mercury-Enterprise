# Publications

Enterprise technical publications metadata for aviation maintenance, flight, engineering, and operations documentation.

## Scope

Mercury tracks **publication metadata, revisions, and licensed storage locators**. It does **not** embed copyrighted OEM manual binaries in the repository.

## Publication type categories

| Category | Examples |
|----------|----------|
| Maintenance manuals | AMM, AIPC/IPC, CMM, SRM, SPM, MPD, SDS, FIM, SSM, WM, WLM, TLMC, NDT, ITEM, GHSI |
| Flight manuals | AFM, FCOM, QRH, MEL, CDL |
| Engineering | EO, EI, ED, ICA, STC, Repair Schemes, CDP |
| Operations | SB, SL, SIL, DDG*, Airport/Ground/Recovery manuals, AW, AMTOSS, APT |

## Revision management

`PublicationRevision` rows are **immutable for content locators and revision numbers**. Lifecycle fields (`status`, `supersedes_revision_id`, `effective_date` when activating) change only through controlled activate/archive transitions. Prior revisions remain historically traceable as `superseded`.

## Storage

See [TECHNICAL_LIBRARY.md](TECHNICAL_LIBRARY.md). Locators only: `external_url`, `object_storage`, `future_ingestion`, or `none`.

## Permissions

| Permission | Roles |
|------------|-------|
| `publication.read` | Viewer+ |
| `publication.manage` | Operator+ |
| `publication.admin` | Administrator (`*`) — archive, access classification, revision activation |

## Operator UI (Sprint 8e)

Technical Library area (`#techLibraryWorkspace`) and Workspace Engine `publication` objects use these APIs. Viewer/Reviewer browse and search. Operator creates metadata and **draft** revisions (`activate: false`). Administrator activates revisions, changes access classification, and archives.

Aircraft **Publications** tab: `GET /publications/by-aircraft/{id}`. Component tab: `GET /publications/by-component/{id}`. AD/SB/EO overviews open a linked publication when `publication_id` is present.

## APIs

`/api/v1/publications/*` and `/api/v1/library/*`

## Audit

`publication.create`, `publication.update`, `publication.revision.create`, `publication.revision.activate`, `publication.archive`, `publication.access_control`

## Explicit non-goals

Document AI/RAG, OCR, and full-text OEM manual ingestion are out of scope; AI-ready stubs live under maintenance (`/api/v1/maintenance/ai/*`).
