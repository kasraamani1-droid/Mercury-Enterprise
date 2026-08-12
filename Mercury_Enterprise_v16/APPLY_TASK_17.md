# MERCURY ENTERPRISE V2.0

## MODULE 12 — HISTORICAL REPORTING AND ANALYTICS
### TASK 17

OBJECTIVE

Build directly on the functionality completed in Tasks 12 through 16 by adding historical reporting, analytics, and KPI visibility to the existing Mercury platform.

This task must turn existing operational history into useful review and executive insight without redesigning the application.

Task 17 must extend the current Mercury application, current dashboard/workspace model, current authentication/session design, current RBAC/approval model, current organization/site scoping, and the audit/provenance foundations established in Task 16.

Human operators remain fully in control.

---

## EXISTING FUNCTIONALITY TO REUSE

Reuse the existing Mercury architecture already present in the repository:

- Task 12 dashboard and existing workspace shell
- Task 13 authentication and session context
- Task 14 RBAC and approval model
- Task 15 organization/site scoping
- Task 16 audit and evidence provenance foundations
- existing incidents, alerts, missions, timeline, connectors, and decisions
- existing History and Executive workspace shells
- existing backend persistence and API foundations
- existing export, history, analytics, executive, and evidence-oriented frontend surfaces where practical

Do NOT create a separate analytics application.

---

## EXACT SCOPE

Add analytics and reporting on top of already-captured Mercury data.

This task must remain incremental from Tasks 12 through 16.

It must extend the existing Mercury data domains and workspace surfaces rather than create a second analytics platform, a second history system, a second evidence reporting path, or a parallel executive dashboard stack.

Focus areas:

- historical summaries
- KPI dashboards
- trend analysis
- operational reporting exports
- executive/history workspace data integration
- scoped reporting by time range, organization, and site
- preservation of audit/provenance distinctions where relevant in historical outputs

Dependencies from previous tasks:

- Task 12 provides the operator-facing dashboard and current workspace baseline.
- Task 13 provides the authenticated identity and session model.
- Task 14 provides RBAC and approval-aware access boundaries.
- Task 15 provides organization/site scoping for all reporting views.
- Task 16 provides auditability and evidence provenance that historical reporting must preserve.

Task 17 must extend the current Mercury reporting surfaces already present in History and Executive workspaces rather than replace them.

---

## ARCHITECTURE CONSTRAINTS

- Reuse existing data domains and workspaces.
- Prefer aggregated read models over duplicate domain logic.
- Reuse the authentication, session, RBAC, site-scoping, audit, and provenance capabilities established in Tasks 13 through 16.
- Reuse the existing History and Executive workspace shells rather than creating dedicated analytics applications or duplicate dashboard pages.
- Do NOT create a second reporting platform or duplicate dashboard stack.
- Do NOT introduce duplicate managers, duplicate APIs, duplicate dashboards, duplicate connectors, or duplicate evidence systems.
- Prefer extending existing incidents, alerts, missions, connectors, decisions, timeline, audit, and evidence data flows over introducing parallel reporting abstractions.
- Preserve current backend route conventions and frontend shell.
- Keep any database change to the absolute minimum and only when strictly necessary for practical reporting performance or durability.
- Keep the design compatible with Tasks 18 through 20, especially connector lifecycle reporting, explainability review, and production observability.

---

## BACKEND REQUIREMENTS

- Add read-oriented analytics/reporting endpoints using existing data sources.
- Reuse incident, mission, alert, connector, timeline, audit, evidence, and decision data.
- Preserve current operational APIs.
- Ensure reports can be scoped by time range, organization, and site.
- Extend existing backend services and route patterns before considering any new abstraction.
- Preserve backward compatibility for current APIs where practical.
- Avoid creating a separate analytics manager, separate reporting service, or parallel evidence reporting subsystem unless extension of existing Mercury components is clearly insufficient.
- Reporting and KPI outputs must remain read-only and derived from existing Mercury domains.
- No unnecessary database schema change is allowed. If any schema change becomes necessary, it must be minimal, explicitly justified, and directly tied to durable or efficient reporting needs.

---

## FRONTEND REQUIREMENTS

- Populate existing History and Executive-oriented surfaces with real analytics data.
- Add KPI cards, trends, and report views without replacing the current UI architecture.
- Preserve current styling and workspace model.
- Reuse the existing frontend shell, workspace navigation, export patterns, history table patterns, and executive KPI surfaces where practical.
- Do NOT create a second analytics dashboard, second history application, or duplicate reporting pages.
- Preserve Task 12 dashboard behavior and Task 13 through Task 16 identity, role, site, audit, and provenance behavior.

---

## API REQUIREMENTS

- Add reporting and analytics endpoints incrementally.
- Keep them read-only.
- Avoid introducing a parallel analytics service or separate API gateway.
- Reuse current API namespaces and route conventions.
- Any new reporting endpoints must be minimal, incremental, site-aware, and reusable by later Tasks 18 through 20.
- Avoid duplicating existing incident, evidence, timeline, connector, or decision history APIs when current Mercury endpoints can be safely extended.

---

## HUMAN-CONTROL / SAFETY REQUIREMENTS

- Reports and analytics must distinguish historical facts from recommendations.
- Decision-support history must remain clearly advisory.
- No analytics output may trigger operational action automatically.
- Human operators remain fully in control.
- No autonomous execution.
- No autonomous decision making.
- No automatic targeting.
- No automatic weapon control.
- No autonomous interception.
- Reporting and analytics must summarize, explain, or visualize history only; they must not automate operational behavior.

---

## TESTS

Add tests for:

- KPI aggregation correctness
- date/site/org scoping
- reporting endpoint behavior
- frontend analytics rendering
- export generation where implemented
- preservation of Task 13 session behavior and Task 14 RBAC behavior in report access
- preservation of Task 15 site/organization scoping in reporting and exports
- preservation of Task 16 audit/provenance distinctions in historical views
- safe failure behavior for unauthorized report or analytics access

Task 16 audit/provenance behavior must continue to pass.

Existing dashboard and API behavior from Tasks 12 through 16 must remain passing unless intentionally expanded.

---

## VERIFICATION

- run backend tests
- run frontend checks/build
- verify history/executive views manually
- verify reporting output against known seeded/test data
- verify authenticated users only see reports allowed by Task 14 role policy and Task 15 site scope
- verify existing History and Executive surfaces can show real analytics without introducing duplicate pages or alternate dashboard paths
- verify exported data preserves audit/provenance distinctions introduced in Task 16 where applicable
- verify report filters for time range, organization, and site behave consistently

Success conditions:

- one Mercury application exposes useful historical reports and KPI views from existing operational data
- reporting behavior reuses the current Mercury architecture and current workspace model
- Task 13 through Task 16 identity, role, site, audit, and provenance rules remain intact
- authorized users can review scoped history and analytics from existing Mercury surfaces

Failure conditions:

- a second reporting platform, second analytics dashboard family, second history system, or duplicate API family is introduced
- reporting bypasses Task 14 role controls or Task 15 site scoping
- analytics views lose or blur Task 16 audit/provenance distinctions where those distinctions are required
- implementation requires unnecessary duplicate managers, duplicate dashboards, duplicate evidence paths, or unnecessary data models
- implementation introduces unnecessary database changes beyond the minimum practical reporting need

---

## GIT INSTRUCTIONS

Before commit:

- `git status`
- `git diff --stat`

Commit message suggestion:

- `Module 12 - Historical Reporting and Analytics`

---

## ACCEPTANCE CRITERIA

- Task 12 dashboard and existing workspace shell remain intact.
- Task 13 authenticated session behavior remains intact.
- Task 14 RBAC and approval boundaries remain intact for all report and analytics access.
- Task 15 organization/site scoping remains intact in all report views and exports.
- Task 16 audit and provenance distinctions remain available where relevant in historical reporting.
- Mercury can produce scoped historical reports and KPIs.
- Existing History and Executive surfaces show real backend-driven data.
- Reporting remains read-only and operator-safe.
- Any new API behavior is incremental, reusable, and compatible with Tasks 18 through 20.
- No duplicate analytics platform, duplicate API family, duplicate dashboard page, duplicate connector reporting path, or duplicate evidence/history path is introduced.
- No unnecessary database schema change is introduced.
- Success and failure behavior for authorized versus unauthorized reporting access is explicit and testable.
- Reporting and analytics remain observational/read-only features only and never introduce autonomous execution or autonomous decision making.
