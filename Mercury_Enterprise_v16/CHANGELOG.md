# Changelog

All notable changes to Mercury Enterprise are summarized here. Package/API version remains `16.0.0` unless noted; sprint tags mark security/ops increments.

## Pilot readiness (workforce API, demo loop, backup)

### Added
- Workforce plan-line HTTP API on existing `workforce_plan_lines`: list/create/GET-by-id/PATCH (status and planner flags) with RBAC and tenant isolation
- Planning desk + Workspace Engine assignment object; work-order overview and aircraft Maintenance tab show package workforce lines
- Idempotent demo assignments on `WP-DEMO-001` (E-1001 technician, E-2001 ACA, E-3001 II) and on check → WP generation
- Closed-loop C-GMEA API walk and sqlite backup/restore tests; compose-aware `pg_dump` via `docker compose exec` when the DB host is `postgres`
- Pilot runbooks under `docs/pilot/` (deploy, demo script, security/network exposure)

### Notes
- Workforce `license_ok` / `authorization_ok` / `available` are planner-entered flags, not a certification determination. No MTBUR/MTBF or invented regulatory rules.
- Default Compose remains LAN/local HTTP on `:3000`. Postgres and Redis are not published. OIDC/SSO is a production blocker for internet-facing paid use — not implemented in this cycle.
- Command/Radar/3D airport twin stay labeled SIM. Demo users live in local `.env` only.

## Publications and personnel operator integration

### Added
- Technical Library desk: manufacturer → family → model → type → ATA browse, search/filters, role-gated publication create, AD/SB/EO chips with `publication_id`
- Workspace Engine `publication` object (revisions, ATA link, admin activate/access/archive) on existing `/api/v1/publications` and `/api/v1/library`
- Aircraft and component **Publications** tabs from `GET /publications/by-aircraft/{id}` and `GET /publications/by-component/{id}`
- Personnel desk: employees, qualification expiry alerts, stamp profiles; Workspace Engine `employee` object
- Job-card personnel context chips (visibility only — inspect/release stay on certification APIs)
- `GET /api/v1/personnel/employees/{id}/stamps` so the UI can list stamp profiles (create already existed)
- Contract suites `backend/tests/test_publications_operator_ui.py` and `backend/tests/test_personnel_operator_ui.py`

### Notes
- No new publications/personnel domains. Storage remains locators only; OEM binaries are not hosted.
- Operator may create publications and draft revisions (`publication.manage`). Archive, access classification, and later revision activation require `publication.admin` (Administrator).
- Creating a stamp profile does not auto-retire prior stamps. Inspect/release authority is not granted by this UI.
- Aviation personas remain documentation-only. Command/Radar/Cloud stay labeled SIM.

## Maintenance planning operator integration

### Added
- Planning Ops desk: live dashboard KPIs, aircraft/urgency/source filters, role-gated generate WP, AD/SB/EO create, deferred defect, MEL/CDL, check, hangar plan, utilization
- Workspace Engine objects for check, AD, SB, EO, MEL item, and finding (deferred defect) on existing `/api/v1/planning` routes
- Aircraft Maintenance tab logs deferred defects; AD/SB tabs list organization directives
- Engineering workspace rows open the same AD/SB/EO objects
- Generate WP from a **selected** due/planned check (not “first only”); 409 on duplicate
- GET-by-id for checks, ADs, SBs, EOs, deferred defects, and MEL items
- Utilization PUT keeps existing FH/FC (and related counters) when those fields are omitted
- Contract suite `backend/tests/test_planning_operator_ui.py`

### Notes
- No new planning domain. Aviation Planner persona remains documentation-only; mutations follow session Operator/Administrator (`planning.manage`).
- AD/SB records are organization-scoped (applicability is text). They are not stored per aircraft.
- Workforce plan CRUD remains deferred. Command/Radar/Cloud stay labeled SIM.

## Enterprise logistics operator integration

### Added
- Logistics Ops operator desk: live dashboard KPIs, search/location/condition filters, waiting-parts job cards, role-gated receive/issue/reserve/release/adjust/warehouse transfer
- Workspace Engine objects for part, material request, purchase order, and tool on existing `/api/v1/logistics` routes
- Work order / job card **Materials** tab: create MR with `job_card_id`/`work_order_id`, approve → reserve → issue → return
- Home logistics KPIs from `GET /logistics/dashboard` (unavailable when live data cannot load)
- Inventory remains a read-only stock table that opens part objects (no second mutation UI)
- Scan lookup opens the resolved part/tool object; identifier APIs only — not a hardware scanner
- Optional `work_order_id` / `job_card_id` filters on `GET /logistics/material-requests`
- `GET /logistics/receipts/{id}` so inspect/putaway can load receipt lines
- Contract suite `backend/tests/test_logistics_operator_ui.py`

### Notes
- No new logistics domain. Direct `/stock/issue` still has no typed work-order fields; job-card linkage is the material-request header.
- Transfers require two distinct warehouses. Same-bin moves are not a separate API.
- Aviation personas remain documentation-only. Stores mutations follow session Operator/Administrator (`logistics.stores`). Reviewer has tools read/mutate, not stock receive/issue.
- Command/Radar/Cloud stay labeled SIM. Payments and OIDC are out of scope.

## Maintenance operations integration

### Added
- Workspace Engine work-order, job-card, aircraft logbook, and aircraft maintenance-context operator UI on existing work-order, maintenance, and planning APIs
- Home operational KPIs from `/work-orders/dashboard` and `/planning/dashboard` (unavailable when live data cannot load)
- Planning due/forecast rows link to aircraft and related work orders; delayed WO list uses order status `delayed`
- Technical Logbook area aircraft filter (`aircraft_id`) and work-order join via job-card `maintenance_task_id`
- Contract suite `backend/tests/test_maintenance_operations_ui.py`

### Notes
- No new backend modules or create-logbook API. ACA release still writes tech-log entries. Job cards have no parallel `#jobCardWorkspace`.
- Mutate controls follow session roles (Operator manage/execute, Reviewer inspect/release, Viewer read). 409 conflicts are shown and not retried automatically.
- PR #8 DD-1001 finding chips and PR #9 Configuration/Components UI remain on the aircraft object.

## Aircraft Components & Configuration Operator UI

### Added
- Aircraft Workspace Engine Configuration and Components tabs load live installed configuration from `/api/v1/components/aircraft/{id}/configuration`
- ATA/system identification via client-side join of catalog + ATA chapters
- Operator install / remove / transfer / register-to-stores forms on existing serialized APIs
- Component object overview and install-history tabs bound to serialized detail and history APIs

### Notes
- No parallel `#componentWorkspace`; PR #8 DD-1001 due-list finding chips remain on the Components tab
- Mutate controls follow session Operator/Administrator roles; 409 details are shown and not retried automatically
- Installed rows are grouped by ATA/system; remove/transfer confirm; occupied positions are blocked before submit
- Workspace Engine ignores stale aircraft loads and keeps the active tab across refresh

## QA-1 — CI pipeline green (RC1)

### Changed
- Work-order demo seed is idempotent per package, order, and job card (missing children are created even when `WP-DEMO-001` already exists)
- Seed regression looks up `wp-demo-c-gmea` / `jc-demo-oil` by id and still lists by aircraft (no coverage drop)
- `frontend/js/config.local.js.example` uses JavaScript comments so `node --check` and the browser accept the local override
- CI runs `python -m pytest` and skips gitignored `config.local.js` in the frontend syntax step

### Notes
- Required CI checks: pytest, `compileall`, frontend `node --check`. Compose/Docker remain best-effort (`continue-on-error`)
- Linting and type checkers are not in the GitHub Actions workflow
- Live PostgreSQL `alembic upgrade head` remains optional (`MERCURY_TEST_DATABASE_URL`)

## RC1 Blocker 06 — End-to-End Smoke Test

### Added
- Sequential smoke suite `backend/tests/test_rc1_e2e_smoke.py` (21 existing workflows, one session)
- Report `docs/engineering/RC1_SMOKE_TEST.md`

### Notes
- No new product features. Sign out UI was already wired (`#ux2SignOut`).
- Complete E2E fails: RBAC admin dropdown, components UI, notification center binding, file input, AI copilot.
- Platform RC1 remains **NO-GO** (77% readiness). Playwright browser E2E still open (RB-08).

## RC1 Blocker 05 — PostgreSQL + Alembic Production Validation

### Changed
- PostgreSQL engines use QueuePool with `pool_pre_ping`, configurable size/overflow, and 1800s recycle
- `get_db()` rolls back the session on exception before close
- Alembic `env.py` registers the full ORM metadata via `import_orm_models()` (autogenerate completeness)

### Added
- Migration suite coverage: full downgrade-to-base, ORM FK/index/unique checks, portable types, ILIKE/`FOR UPDATE` compile, session rollback, Compose health gate
- Pooling knobs `MERCURY_DB_POOL_SIZE`, `MERCURY_DB_MAX_OVERFLOW`, `MERCURY_DB_POOL_RECYCLE`

### Notes
- Live Postgres `upgrade head` remains optional via `MERCURY_TEST_DATABASE_URL` (not run on the Windows RC1 host without Docker)
- Verdict for PostgreSQL production database: **GO** at **91%** readiness (live host verification pending)
- Restored missing `from .websocket.manager import manager` so incident create can broadcast after commit (NameError found during validation)

## RC1 — API Documentation

### Changed
- OpenAPI enrichment documents every operation with tag, description (auth, tenant, permission, validation), security schemes, and error responses
- Connector tag normalized to `connectors`; full tag catalog for Swagger UI / ReDoc
- Login request schema includes an example; approval payload fields have descriptions

### Added
- `backend/app/openapi_docs.py` (documentation only)
- Regression suite `backend/tests/test_rc1_api_documentation.py`
- Operator guide `docs/engineering/API_DOCUMENTATION.md`

## RC1 Blocker 03 — Approval Persistence (verified)

### Changed
- Approve and consume load the SQL row with `SELECT … FOR UPDATE` before status checks
- Operator guide documents logout/login, history list, 409 transitions, and explicit non-goals (no reject API)

### Added
- Regression coverage in `test_approval_persistence.py`: logout/login survival, consumed history, double approve/consume, consume error handling

## RC1 Blocker 02 — Tenant Isolation

### Changed
- Incident status, events, and evidence mutate only via `_get_scoped_incident` (org/site); cross-tenant UUID access returns 404
- Incident/timeline WebSocket broadcasts pass `organization_id`/`site_id` so other tenants never receive the payload
- Alerts list/ack and dashboard alert counts use the existing AlertManager tenant filter
- Incident write audits stamp the resource tenant, not only the session copy

### Added
- Regression suite `backend/tests/test_rc1_tenant_isolation.py`
- Operator guide `docs/engineering/TENANT_ISOLATION.md`

## RC1 Blocker 01 — Authentication

### Changed
- Session store no longer persists already-expired records (TTL ≤ 0 deletes); heartbeat sweeps expired memory sessions
- Login rate-limit `429` writes `security.login_failure` with `details=rate_limited`
- OpenAPI documents an `auth` tag and `SessionCookie` security scheme (opaque cookie; JWT is not a session mechanism)
- Frontend re-opens the login overlay on `401` from authenticated API calls (`mercury:auth-required`)

### Added
- Regression suite `backend/tests/test_rc1_authentication.py`
- Operator guide `docs/engineering/AUTHENTICATION.md`

## RC1 Blocker 05 — PostgreSQL Migration

### Changed
- Alembic `env.py` documents SQLite batch mode for autogenerate; revisions `0005`–`0008` use `batch_alter_table` for constraint/default ALTERs (no-op wrapper on PostgreSQL)
- Backend Docker image ships `alembic/`, `alembic.ini`, and `docker-entrypoint.sh`; entrypoint runs `alembic upgrade head` when `DATABASE_URL` is PostgreSQL
- Compose backend defaults `DATABASE_URL` to the Compose Postgres service

### Added
- Migration suite `backend/tests/test_postgresql_migrations.py` (history, clean install, idempotent upgrade, downgrade `-1`, prod config)
- Operator guide `docs/engineering/POSTGRESQL_MIGRATIONS.md`

## RC1 Blocker 04 / RB-05 — Password Security

### Changed
- Login passwords use **Argon2id** with unique salts (`backend/app/security/operators.py`); legacy SHA-256(pepper) verifies once then rehashes
- Admin password reset (`POST /admin/users/password`) revokes all sessions for that operator
- Production continues to refuse the development pepper as `COOKIE_SECRET` / `JWT_SECRET`
- Docs: Identity, SECURITY, EPIC-009 RC notes, Data Model column width, signature ADR hygiene notes

### Added
- Automated suite `backend/tests/test_password_security.py` (hash uniqueness, login, reset, session revocation, legacy upgrade)

## RC1 Blocker 03 — Approval Persistence

### Changed
- Approvals moved from in-process `_approvals` dict to durable SQL `approval_requests`
- List/approve/consume are org/site scoped; Alembic `20260814_0022`
- Regression tests in `test_approval_persistence.py`; docs: `docs/engineering/APPROVAL_PERSISTENCE.md`

## EPIC-002 — Frontend Completion

### Added
- Aircraft register + filter/sort; WO create board; marketplace cart/quote; approvals inbox; tech library; OEM catalog shell
- Digital Logbook and Engineering AD/SB/EO bound to live APIs; Developer installations/subscriptions/DLQ
- Workspace Engine: real `createWo` / `openTwin` / cart / quote actions; twin reliability & relationships tabs
- SIM chrome labels for Command / Radar / Cloud / Ops Airport Twin
- Notes: `docs/engineering/EPIC002_FRONTEND_COMPLETION.md`

## Task 36 — Mercury AEOS Constitution

### Added
- Master Constitution v1.0: platform/API/cloud/event/twin/AI/security/multi-tenant/offline/mobile/integration/extensible/observable/testable/documented principles
- Engineering, Architectural, and Product standards; governance recommendations
- ADR-0018; index under `docs/constitution/`

### Notes
- Documentation only — no runtime code changes.

## EPIC-003 — Backend Completion

### Added
- Runtime authz merges temporary access + custom roles (`security/runtime_authz.py`) across domain routers
- Fleet registration GET/PATCH; logistics PO workflow bridge; publications `local_filesystem` storage
- OpenAPI tag descriptions for Programs 13–17; marketplace org-scope + temp-access regression tests

## EPIC-001 — Platform Hardening

### Added
- Event Framework → Fabric dual-write for mapped bus types; ownership matrix + soft-delete policy
- Pagination hard caps on fleet/org/personnel/publications/planning/approvals/incidents
- Local disk platform file upload (`/api/v1/platform/files/upload`); Redis fail-closed startup/ready
- Engineering docs: `docs/engineering/CI.md`, `EPIC001_PLATFORM_HARDENING.md`

## EPIC-009 — Security (productization)

### Added
- Redis-backed session store (`security/sessions.py`) with in-memory fallback; Compose `redis` service
- Optional machine API key auth (`security/api_key.py`) when `MERCURY_API_KEY` is set
- Tenant isolation + session/API-key/cookie Secure regression tests (`test_epic009_security.py`)
- Docs: `docs/security/EPIC009_RC_NOTES.md`; SECURITY.md updated (OIDC deferred for RC)

## Task 27 — Mercury Workspace Engine

### Added
- Context-oriented Workspace Engine (`frontend/js/workspace-engine/`): open objects (Aircraft, Engine, APU, Work Order, Inspection, Finding, Component, Marketplace Listing, Supplier, Organization, Engineer, Planner, Technician, QA, Project, Digital Twin)
- Per-object tabs, timeline, pinned widgets, comments, attachments rail, AI panel, quick actions
- Object sessions in global tab bar; command palette `aircraft <id>` open; deep links `#/object/{type}/{id}`
- Docs: `docs/ux/WORKSPACE_ENGINE_*.md`

### Notes
- No new backend modules. Lists open objects; domain boards remain for bulk work.

## Task 19 — Mercury Enterprise UX 2.0

### Added
- Design system tokens (IBM Plex, dark/light), UX shell (sidebar IA, workspace tabs, command palette, shortcuts, favorites/pins)
- Landing Dashboard + Aircraft/Fleet/Work Orders/Logbook/Engineering/Inventory/Marketplace/Asset Twin/Authority/Organization/AI/Developer workspaces
- Frontend modules under `frontend/js/ux2/`; CSS `design-system.css`, `ux2-shell.css`
- Docs: `docs/ux/*` (review, navigation, wireframes, component inventory, roadmap, production readiness, design system)

### Notes
- No new backend modules. Legacy Command/Planning/Maintenance/Logistics modules preserved.

## Program 17 — Mercury Enterprise Event Fabric

### Added
- Durable Event Fabric: versioned catalog, immutable store, subscriptions, DLQ/retry, replay, correlation/trace observability
- API `/api/v1/event-fabric`; permissions `event_fabric.read|manage`; Alembic `20260814_0020`
- Event Framework PlatformEvent extended with trace/actor/severity/duration/version fields
- Docs: EVENT_FABRIC_ARCHITECTURE, EVENT_CATALOG, EVENT_FLOW_DIAGRAMS, API/roadmap/readiness; ADR-0017
- Tests: `test_event_fabric_program_17.py`

## Program 16 — Mercury Plugin Platform

### Added
- Plugin catalog for Garmin, Honeywell, drone inspection, NDT, flight ops, accounting, custom dashboards, ERP, SMS (Safety Management System), weather, fuel planning
- Org installations + dashboard layouts; Connect connectors expanded (`oem.garmin`, `oem.honeywell`, `inspection.drone`, `ndt.generic`, `dashboard.custom`, `safety.sms`, `fuel.planning`)
- API `/api/v1/plugins`; permissions `plugins.read|manage`; Alembic `20260814_0019`
- Docs: PLUGINS_ARCHITECTURE/API/FUTURE_ROADMAP/PRODUCTION_READINESS; ADR-0016
- Tests: `test_plugins_program_16.py`

## Program 15 — Mercury Digital Twin

### Added
- Digital Twin lifecycle domain `backend/app/twin/`: permanent UUID twins, Fabric passport binding, immutable history, configuration baselines, architecture-only reliability, search
- API `/api/v1/twin`; permissions `twin.read|manage`; Alembic `20260814_0018`
- Docs: DIGITAL_TWIN_ARCHITECTURE/GUIDE, TWIN_* diagrams/API/roadmap/readiness; ADR-0015; Digital Passport guide updated
- Tests: `test_twin_program_15.py`

## Program 14 — Mercury Aviation Network

### Added
- Secure professional collaboration domain `backend/app/network/`: org/professional profiles, partnerships, collaborations, document shares, messaging, events, directory
- Isolation by default; cross-org actions gated by active partnership permissions
- API `/api/v1/network`; permissions `network.read|manage`; Alembic `20260814_0017`
- Docs: NETWORK_ARCHITECTURE, ENTITY_RELATIONSHIP, WORKFLOW, API, FUTURE_ROADMAP, PRODUCTION_READINESS; ADR-0014
- Tests: `test_network_program_14.py`

## Program 13 — Mercury Digital Marketplace

### Added
- B2B aviation commerce on `backend/app/marketplace/`: sellers, products, cart, quotes, orders/lines, reviews, favorites, saved searches
- Catalog categories (parts→consulting), pricing/inventory/search APIs; legacy listings retained
- Verification badges + payment_status as architecture readiness only (no regulatory/PSP claims)
- Alembic `20260814_0016`; Fabric entity types for seller/product/order/quote
- Docs: MARKETPLACE_ARCHITECTURE, BUSINESS_MODEL, ENTITY_RELATIONSHIP, WORKFLOW, API, FUTURE_ROADMAP, PRODUCTION_READINESS; ADR-0013
- Tests: `test_marketplace_program_13.py`

## Program 12 — Aviation Digital Ecosystem

### Added
- Stakeholder ecosystems (Airline, BizAv, MRO, CAMO, OEM, Supplier, Repair Station, Authority, Training, Careers, Marketplace) with capability maps and tenant enrollments
- Mercury Connect connector catalog + org bindings (vault refs only)
- APIs `/api/v1/ecosystem`, `/api/v1/connect`; permissions `ecosystem.*` `connect.*`; Alembic `20260814_0015`
- Docs: AVIATION_DIGITAL_ECOSYSTEM, PRODUCT_PORTFOLIO, MERCURY_CONNECT, ECOSYSTEM_SEQUENCE, ECOSYSTEM_PRODUCTION_READINESS; ADR-0012
- Tests: `test_ecosystem_program_12.py`

## Program 11 — Universal Data Fabric

### Added
- `backend/app/fabric/`: Digital Passports, entity-type catalog, relationship engine, fabric events, tags, attachment refs, retention policies, legal holds
- Digital Thread traversal API; universal fabric search with platform search mirror + AI metadata
- REST `/api/v1/fabric/*`; permissions `fabric.read|manage`; Alembic `20260814_0014`
- Docs: UNIVERSAL_DATA_FABRIC, DIGITAL_THREAD, DIGITAL_PASSPORT, KNOWLEDGE_GRAPH, ENTITY_RELATIONSHIP, DATA_DICTIONARY, FABRIC_PRODUCTION_READINESS; ADR-0011
- Tests: `test_fabric_program_11.py`

## AEOS Architecture Standardization

### Added
- Shared primitives (`backend/app/shared/`), Audit Engine, Permission Service, Event Framework, Integration Framework, Workflow Bridge
- Marketplace / OEM / Authority readiness domains with seeded registries and APIs
- Job-card transitions resolved from generic workflow definition `work_order.job_card`
- Search `ai_metadata_json` for AI readiness (no LLM)
- Docs: `docs/architecture/*`, ADR-0010; Alembic `20260814_0013`
- Tests: `test_aeos_architecture.py`

## Program A — Enterprise Platform Foundation

### Added
- Shared platform package `backend/app/platform/`: identity (API keys, PATs, MFA enrollment), org extensions (business units, cost centers, facilities), RBAC extensions (templates, custom roles, temporary access, permission audit), generic workflow engine, multi-channel notifications, versioned file metadata, global search index, settings/feature flags
- REST API `/api/v1/platform/*`; permissions `platform.read` / `platform.manage`; Alembic `20260813_0012`
- Docs: [PLATFORM_OVERVIEW.md](docs/PLATFORM_OVERVIEW.md), ADR-0009 platform foundation shared substrate
- Tests: `backend/tests/test_platform_program_a.py`

## Program B — Enterprise Logistics

### Added
- Integrated logistics package: warehouse hierarchy, part master, stock ledger (FIFO/FEFO), rotables, tool crib, material requests, PR→RFQ→PO→receive→inspect→putaway→invoice, vendors, shipments, scan API
- Automatic material/tool planning bridge from Sprint 9 work-package generation; shortages dashboard
- Permissions `logistics.read|manage|stores|purchase|tools|finance`; Alembic `20260813_0011`; Logistics UI tab
- Docs: WAREHOUSE, INVENTORY, PART_MASTER, SERIALIZED_PARTS, ROTABLES, TOOLS, PURCHASING, VENDORS, BARCODE_RFID, MATERIAL_PLANNING

## Sprint 9 — Maintenance Planning & Aircraft Maintenance Program

### Added
- Maintenance programs with immutable revisions; MPD tasks with multi-unit intervals
- Maintenance checks (preflight through D/structural/engine/custom) with due computation
- Airworthiness Directives, Service Bulletins, Engineering Orders (approve workflow)
- MEL/CDL items, deferred defects with expiry/alerts
- Aircraft utilization counters, traffic lights, hangar/parts/tool/workforce plan lines
- Forecast engine (30/90/180/365) + urgency-sorted due list + planner dashboard + aircraft status
- Automatic Work Package / Work Order / Job Card generation into Sprint 8 execution
- Permissions `planning.read` / `planning.manage`; Alembic `20260813_0010`; Planning UI tab
- Docs: MAINTENANCE_PROGRAM, MPD, FORECAST_ENGINE, PLANNING_DASHBOARD, AD/SB/EO, MEL_CDL, DEFERRED_DEFECTS, AIRCRAFT_STATUS, HANGAR/WORKFORCE planning

## Sprint 8 — Work Orders, Job Cards & Maintenance Execution

### Added
- Work packages, work orders, job cards, and attachments with org isolation and validated job-card status transitions
- Job cards bridge to MaintenanceTask for certify → technical logbook → aircraft/component history (no duplicate engine)
- Execution APIs: assign, transition, complete-work, inspect (approve/reject/rework/independent), ACA release
- Role dashboards (manager/planner/supervisor/technician/QA/ACA) and MRO reports
- Maintenance workspace UI: planning board, technician board, supervisor assign, QA/ACA queues, library shortcuts, offline sync queue
- Permissions `work_order.read|manage|execute`; seed independent inspector E-3001 for segregation of duties
- Alembic `20260813_0009_work_orders_job_cards`; docs `WORK_PACKAGES.md`, `WORK_ORDERS.md`, `JOB_CARDS.md`, `TECHNICIAN_WORKFLOW.md`, `ACA_RELEASE.md`, `MAINTENANCE_EXECUTION.md`

### Hardened (production readiness)
- Certification-gated statuses (`waiting_inspection` / `completed` / `released`) blocked on `/transition`
- Performed ≠ inspected segregation; technician ACA auth revoked in seed
- Release requires immutable publication revision + ATA; logbook snapshots revision number/date and cert requirements
- Double-release / released-card mutation guards; inspect scoped to waiting_inspection (+ II on completed)
- Fail-closed audit on complete/inspect/release; append-only logbook amendment API
- Offline complete syncs via `complete-work` (not bare transition); unsigned PKI methods rejected until providers exist

## Sprint 7b — Technical Library, Personnel & Maintenance Certification

### Added
- Expanded publication types (maintenance / flight / engineering / operations) with revision history and library browse
- Aircraft families, alternate parts / interchangeability, personnel qualifications & ACA authorizations
- Maintenance Task Engine (scheduled/unscheduled/corrective/preventive/inspections/checks/troubleshooting/replacement/deferred/MEL-CDL/SB/EO) with library revision binding, certification flags, release → technical logbook, audit trail API
- Critical-task policies, immutable digital signatures, certification chain, technical logbook
- AI-ready index / embedding / cross-ref stubs (no AI compute); enterprise RBAC permission expansion + persona map
- Production-readiness hardening: certify credential + authority/expiry checks, task lifecycle transitions, release→component history, publication activate RBAC fix, library types WDM/SDM/TSM/MFIM, family browse API, pagination
- Alembic `20260813_0005`–`20260813_0008`; docs for publications, library, personnel, tasks, certification, signatures, logbook, RBAC

## Sprint 7 — Aircraft Components & Configuration Management

### Added
- ATA chapters, component catalog, serialized components, immutable installation history
- Install / remove / transfer flows with TSN/CSN/TSO/CSO decimal hour tracking and optional life limits
- Aircraft configuration API; permissions `component.*` / `configuration.*`
- Alembic `20260812_0004_aircraft_components`; docs `docs/AIRCRAFT_CONFIGURATION.md`

## Sprint 6 — Aircraft Registry & Fleet Management

### Added
- Aviation domain: manufacturers, aircraft models, statuses, fleet operators, fleets, aircraft, registrations
- Alembic migration `20260812_0003_aircraft_registry`
- REST APIs under `/api/v1/fleet/*` with org isolation, audit events, and seed catalog/demo fleet
- Permissions `fleet.read` / `fleet.manage`; dashboard `fleet_health.aircraft_online` from registry
- Docs: `docs/FLEET_REGISTRY.md`

## Sprint 5 — Enterprise Organizations & Multi-Tenancy

### Added
- Persisted hierarchy: companies, organizations, sites, departments, teams, org users, memberships
- Alembic migration `20260812_0002_enterprise_organizations`
- REST APIs under `/api/v1/companies|organizations|sites|departments|teams|org/users|memberships|org/me`
- Membership-aware session context (`auth/context`) and org-scoped role resolution
- Idempotent aviation seed (East/West orgs and sites) with operator memberships
- Permissions `org.read` / `org.manage`; docs in `docs/ORGANIZATIONS.md`

### Security
- Context switches denied without organization membership (platform admin exempt)
- Organization list/site APIs filtered by membership

## v0.9.2 — Enterprise Observability & Operations

### Added
- JSON structured logging with request, correlation, and user IDs; optional rotating file logs
- Enriched `/health`, `/ready`, `/live` (database, optional Redis, disk, memory, versions, uptime)
- Prometheus metrics at `/metrics` and admin JSON snapshot at `/admin/metrics`
- Administrator APIs: `/admin/system`, `/admin/health`, `/admin/metrics`, `/admin/audit`
- Expanded audit actions (login failure, user/password/role/config changes, optional API access)
- Hashed in-memory operator directory with admin user management endpoints
- Backup scripts: `scripts/backup_database.sh`, `restore_database.sh`, `verify_backup.sh`
- Docs: `docs/OBSERVABILITY.md`, `AUDIT_LOGGING.md`, `BACKUP.md`, `MONITORING.md`

### Security
- Rate-limit blocks metered without request-path DB writes under flood
- API-access audit opt-in (`MERCURY_AUDIT_API_ACCESS`, default off)
- Last-Administrator demotion blocked

## v0.9.1 — Production Security & Infrastructure

### Added
- Edge NGINX HTTPS (TLS 1.2/1.3, Let's Encrypt, HTTP→HTTPS redirect)
- Security headers, reverse-proxy WS/gzip/timeouts/upload limits
- Application + NGINX rate limiting (HTTP 429)
- Compose production profile (`nginx`, `certbot`), healthchecks, restart policies
- Root probes `/health`, `/ready`, `/live`
- `docs/security/HTTPS.md`, production env validation (`JWT_SECRET`, `COOKIE_SECRET`, …)

## 16.0.0 — Mercury Enterprise V2.0

### Added
- Production-oriented FastAPI lifespan and configuration
- PostgreSQL Docker deployment with persistent volume
- NGINX frontend/reverse proxy
- WebSocket live event gateway and heartbeat
- Health and readiness probes
- Session RBAC, audit, decisions, connectors, reporting
- Request IDs, structured logging, generic error responses
- GitHub Actions CI
- Architecture, security, and production-readiness guides

### Retained
- Full Mercury simulated enterprise command workspaces and operational demonstration features

### Limitation
- Not certified or approved for real aviation, defence, surveillance, emergency-response, or safety operations

## 15.0.0

### Added
- Production-oriented FastAPI lifespan and configuration
- PostgreSQL Docker deployment with persistent volume
- NGINX frontend/reverse proxy
- WebSocket live event gateway and heartbeat
- Health and readiness probes
- Optional API-key protection for write endpoints
- Request IDs, response timing, structured logging, and generic error responses
- GitHub Actions CI
- Architecture, security, and production-readiness guides

### Retained
- Full Mercury simulated enterprise command workspaces and operational demonstration features

### Limitation
- Not certified or approved for real aviation, defence, surveillance, emergency-response, or safety operations
