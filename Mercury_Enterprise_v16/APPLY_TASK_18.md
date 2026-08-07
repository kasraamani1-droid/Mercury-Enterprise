# MERCURY ENTERPRISE V2.0

## MODULE 13 — CONNECTOR LIFECYCLE AND RESILIENCE
### TASK 18

OBJECTIVE

Build directly on the functionality completed in Tasks 12 through 17 by strengthening connector lifecycle management, health history, and ingestion resilience within the existing Mercury platform.

This task must improve the reliability, diagnosability, and operational visibility of the current integration layer without redesigning the application.

Task 18 must extend the current Mercury application, current connector architecture, current dashboard/workspace model, current authentication/session design, current RBAC/approval model, current organization/site scoping, and the audit/reporting/analytics foundations established in Tasks 16 and 17.

Human operators remain fully in control.

---

## EXISTING FUNCTIONALITY TO REUSE

Reuse the existing Mercury architecture already present in the repository:

- Task 12 dashboard and existing workspace shell
- Task 13 authentication and session context
- Task 14 RBAC and approval model
- Task 15 organization/site scoping
- Task 16 audit and provenance foundations
- Task 17 reporting and analytics foundations
- existing ConnectorManager
- existing connector models, providers, registry, and routes
- existing connector visibility already surfaced in current dashboard and integrations/admin-oriented workspaces
- existing alerts, timeline, audit, reporting, and analytics structures

Do NOT create a second connector framework, a second ingestion subsystem, or a separate connector health platform.

---

## EXACT SCOPE

Extend the current connector subsystem with stronger lifecycle, resilience, and observability behavior.

This task must remain incremental from Tasks 12 through 17.

It must extend the existing Mercury connector architecture rather than create a second integration-management platform, a second health system, a second connector dashboard family, or a parallel ingestion pipeline.

Focus areas:

- connector health history
- start/stop/recovery visibility
- degraded/error state handling
- retry/backoff policy where needed
- operator/admin diagnostics
- analytics integration for connector reliability
- scoped connector visibility by organization/site where applicable

Dependencies from previous tasks:

- Task 12 provides the current dashboard and operator-facing connector visibility baseline.
- Task 13 provides authenticated identity and session context.
- Task 14 provides RBAC and approval-aware access boundaries for connector controls.
- Task 15 provides organization/site scoping that connector visibility and actions must preserve.
- Task 16 provides auditability and provenance requirements for connector state changes and operator actions.
- Task 17 provides reporting and analytics foundations that connector reliability metrics should reuse.

Task 18 must explicitly build on connector visibility already surfaced in Tasks 12 and 17 and must remain compatible with the explainability and production-hardening work planned in Tasks 19 and 20.

---

## ARCHITECTURE CONSTRAINTS

- Reuse existing ConnectorManager, provider, registry, and connector route architecture.
- Preserve current connector API conventions where possible.
- Reuse the authentication, session, RBAC, site-scoping, audit, reporting, and analytics capabilities established in Tasks 13 through 17.
- Reuse the existing dashboard, admin, integrations, cloud, and compliance-oriented workspace shells where practical rather than creating duplicate connector lifecycle pages.
- Do NOT create duplicate ingestion managers, duplicate health subsystems, duplicate connector APIs, duplicate dashboard pages, or duplicate evidence/reporting paths.
- Prefer extending existing connectors, alerts, timeline, audit, and reporting flows over introducing parallel lifecycle abstractions.
- Keep changes compatible with multi-site scoping from Task 15 and future explainability and observability work in Tasks 19 and 20.
- Database schema changes should only be introduced if absolutely required and explicitly justified.

---

## BACKEND REQUIREMENTS

- Extend the existing connector lifecycle and health model.
- Persist or expose connector health history where justified.
- Reuse alerts, timeline, audit, reporting, and analytics mechanisms for connector state changes.
- Preserve current polling and provider patterns.
- Extend existing backend services and route patterns before considering any new abstraction.
- Preserve backward compatibility for current connector and operational APIs where practical.
- Avoid creating a separate connector lifecycle manager, separate reliability service, or parallel connector history subsystem unless extension of existing Mercury components is clearly insufficient.
- Connector lifecycle and resilience outputs must remain integrated with the current Mercury platform and current reporting chain.
- Database schema changes are allowed only if strictly necessary for durable connector health history or resilience telemetry, and must be minimal and explicitly justified.

---

## FRONTEND REQUIREMENTS

- Extend existing connector, admin, integrations, dashboard, or cloud-oriented surfaces with lifecycle and health visibility.
- Provide operator/admin-friendly diagnostics.
- Preserve current frontend architecture and workspace model.
- Reuse existing health/status, dashboard summary, integrations catalog, and admin visibility patterns where practical.
- Do NOT create a second connector dashboard, second integrations application, or alternate lifecycle UI path.
- Preserve Task 12 dashboard behavior and Task 13 through Task 17 identity, role, site, audit, reporting, and analytics behavior.

---

## API REQUIREMENTS

- Extend current connector endpoints incrementally.
- Add read/write lifecycle controls only where appropriate and role-protected.
- Avoid creating a parallel integration-management API family.
- Reuse current API namespaces and route conventions.
- Any new lifecycle or health-history endpoints must be minimal, incremental, site-aware where relevant, and reusable by Tasks 19 and 20.
- Avoid duplicating existing connector, alert, timeline, audit, or reporting APIs when current Mercury endpoints can be safely extended.

---

## HUMAN-CONTROL / SAFETY REQUIREMENTS

- Connector lifecycle actions must be explicit human operations where they affect production behavior.
- Connector failure recovery must not imply autonomous operational action execution.
- Degraded data quality must be visible to operators.
- Human operator always remains in control.
- No autonomous execution.
- No autonomous decision making.
- No autonomous targeting.
- No autonomous interception.
- No automatic weapon control.
- Connector resilience and recovery behavior must improve visibility and control, not automate operational decisions.

---

## TESTS

Add tests for:

- connector state transitions
- degraded/error behavior
- retry/recovery logic
- connector health history
- UI rendering of lifecycle diagnostics
- preservation of Task 13 session behavior and Task 14 RBAC behavior for connector actions
- preservation of Task 15 site/organization scoping in connector visibility and lifecycle actions
- preservation of Task 16 audit/provenance requirements for connector state changes
- preservation of Task 17 reporting/analytics behavior where connector reliability data is surfaced
- safe failure behavior for unauthorized lifecycle actions or invalid connector state transitions

Task 17 reporting/analytics behavior must continue to pass.

Existing dashboard and API behavior from Tasks 12 through 17 must remain passing unless intentionally expanded.

---

## VERIFICATION

- run backend tests
- run frontend checks/build
- verify connector lifecycle views manually
- verify state changes publish expected visibility through existing systems
- verify authenticated users only see or control connector actions allowed by Task 14 role policy and Task 15 site scope
- verify existing dashboard, admin, and integrations surfaces can show lifecycle and health information without introducing duplicate pages or alternate dashboard paths
- verify connector health history and reliability state flow into reporting/analytics surfaces where applicable
- verify degraded, error, recovery, and retry states are visible and understandable in existing Mercury surfaces

Success conditions:

- one Mercury application exposes meaningful connector lifecycle, health, and resilience visibility
- connector lifecycle behavior reuses the current Mercury architecture and current workspace model
- Task 13 through Task 17 identity, role, site, audit, reporting, and analytics rules remain intact
- authorized operators/admins can inspect and manage connector lifecycle behavior using existing Mercury surfaces and APIs

Failure conditions:

- a second connector framework, second ingestion subsystem, second lifecycle dashboard family, or duplicate API family is introduced
- connector lifecycle controls bypass Task 14 role protections or Task 15 site scoping
- connector state changes are not visible in the audit/reporting chain established by Tasks 16 and 17
- implementation requires unnecessary duplicate managers, duplicate dashboards, duplicate models, or unnecessary data structures
- implementation introduces database changes that are not strictly required and explicitly justified

---

## GIT INSTRUCTIONS

Before commit:

- `git status`
- `git diff --stat`

Commit message suggestion:

- `Module 13 - Connector Lifecycle and Resilience`

---

## ACCEPTANCE CRITERIA

- Task 12 dashboard and existing workspace shell remain intact.
- Task 13 authenticated session behavior remains intact.
- Task 14 RBAC and approval boundaries remain intact for connector visibility and control.
- Task 15 organization/site scoping remains intact in all connector lifecycle and health views.
- Task 16 audit and provenance expectations are preserved for connector state changes where applicable.
- Task 17 reporting and analytics remain compatible with connector lifecycle and reliability outputs.
- Existing ConnectorManager is extended, not replaced.
- Mercury exposes meaningful connector lifecycle and reliability information.
- Operators/admins can understand degraded integration states using existing Mercury surfaces.
- Any new API behavior is incremental, reusable, and compatible with Tasks 19 and 20.
- No duplicate connector framework, duplicate API family, duplicate dashboard page, duplicate manager, or parallel data model is introduced when existing Mercury structures can be extended.
- Database schema changes, if any, are minimal, strictly necessary, and explicitly justified.
- Connector lifecycle and resilience features remain operator-controlled and never introduce autonomous execution or autonomous decision making.
