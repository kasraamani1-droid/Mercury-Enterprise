# MERCURY ENTERPRISE V2.0

## MODULE 10 — ORGANIZATION AND MULTI-SITE OPERATIONS
### TASK 15

OBJECTIVE

Build on the RBAC and approval controls completed in Task 14 by introducing organization-aware and multi-site operational support.

The platform must support multiple airports/sites without creating a second Mercury instance.

---

## EXISTING FUNCTIONALITY TO REUSE

Reuse:

- authenticated identity and roles from Tasks 13 and 14
- existing MissionService / MissionManager
- existing ConnectorManager
- existing dashboard and workspace shell
- existing incidents, timeline, alerts, and decision-support flows

Do NOT create a second mission platform or duplicate site managers if existing mission and resource systems can be extended.

---

## EXACT SCOPE

Extend Mercury to support organization-scoped and site-scoped operations.

This task must build directly on Task 14.

It must extend the authenticated, role-aware, approval-aware Mercury application already defined by Tasks 12 through 14 rather than introducing a separate multi-tenant or per-site platform.

Focus areas:

- organizations and site context
- airport/site selection
- scoping of missions, alerts, connectors, and dashboards
- site-aware operator visibility
- safe defaults for cross-site data access

This task must explicitly build on the identity and role boundaries completed in Task 14.

Task 15 should remain a scoped extension of the current Mercury application shell, APIs, mission/resource/connector structures, and dashboard/workspace surfaces.

Do NOT create a second site management system, a parallel dashboard family, or a second Mercury instance.

---

## ARCHITECTURE CONSTRAINTS

- Extend current mission/resource/connector architecture.
- Preserve the single Mercury application structure.
- Do NOT create a separate per-site application.
- Avoid duplicate managers when existing services can be extended.
- Keep changes compatible with future analytics and reporting tasks.
- Reuse the authentication, session, RBAC, and approval model established in Tasks 13 and 14.
- Reuse the current frontend application shell and workspace model.
- Do NOT introduce duplicate site-scoping APIs, duplicate dashboard pages, or duplicate mission/resource/connector abstractions.
- Prefer additive scoping of existing Mercury domains over creation of new parallel organizational layers.

---

## BACKEND REQUIREMENTS

- Support organization/site scoping in existing backend domains.
- Reuse current mission, alert, connector, timeline, and decision structures.
- Preserve current route conventions.
- Ensure site scoping works with Task 14 roles and approval behavior.
- Extend existing services and managers before considering any new backend abstraction.
- Preserve backward compatibility for current APIs where practical.
- Avoid creating a separate organization manager or separate site manager unless extension of current Mercury components is proven insufficient.
- No database schema change is required unless a minimal and clearly justified scoping model is proven necessary during implementation.

---

## FRONTEND REQUIREMENTS

- Add organization/site context to the existing frontend shell.
- Support operator selection or switching of active site where permitted.
- Update dashboard and workspace views to reflect the current site scope.
- Preserve the current workspace model and visual language.
- Reuse the existing airport/site selection patterns already present in the frontend where practical.
- Reuse the existing Command, Executive, History, Admin, Integrations, and Compliance workspace shells rather than creating site-specific duplicate pages.
- Preserve Task 12 dashboard behavior and Task 14 role/approval behavior.

---

## API REQUIREMENTS

- Extend existing APIs with organization/site context where required.
- Preserve backward compatibility where practical.
- Avoid creating duplicate site-specific API families.
- Reuse current API namespaces and route conventions.
- Any new organization/site context must be incremental, consistent, and reusable by future audit, reporting, and analytics tasks.
- Avoid parallel “multi-site” endpoints when current Mercury endpoints can be safely extended.

---

## HUMAN-CONTROL / SAFETY REQUIREMENTS

- Site changes must be explicit human actions.
- Operators must not accidentally act outside their authorized organization/site scope.
- Decision-support remains advisory in all sites.
- No autonomous execution of operational actions.
- No automatic targeting, firing, interception, or weapon control.
- Site scoping must constrain and clarify human action, not automate it.

---

## TESTS

Add tests for:

- organization/site scoping of data
- role-restricted site access
- mission and alert filtering by site
- frontend site switch behavior
- safe handling of mixed-site dashboards
- connector and dashboard scoping by site
- preservation of Task 14 role/approval behavior under site restrictions
- safe failure behavior when a user attempts to access an unauthorized site

Task 14 role enforcement must continue to pass.
Existing dashboard and API behavior from Tasks 12 through 14 must remain passing unless intentionally expanded.

---

## VERIFICATION

- run backend tests
- run frontend checks/build
- verify multi-site operator flows manually
- verify unauthorized cross-site access is blocked
- verify an authorized operator can change site context only where allowed
- verify dashboard/workspace data updates to the selected site scope without creating alternate dashboard paths
- verify role and approval behavior from Task 14 still applies after site context is introduced
- verify unauthorized site selection or cross-site access fails safely and visibly
- verify no duplicate workspace pages or API families are introduced

Success conditions:

- one Mercury application supports scoped multi-site behavior
- authorized users can work within allowed organization/site scope
- existing dashboard and workspace patterns remain intact
- Task 14 authorization and approval rules still apply within site context

Failure conditions:

- users can access data outside authorized organization/site scope
- a second dashboard path, second site-specific frontend, or duplicate API family is introduced
- Task 14 role or approval protections are bypassed by site switching
- multi-site behavior requires unnecessary duplicate managers or models

---

## GIT INSTRUCTIONS

Before commit:

- `git status`
- `git diff --stat`

Commit message suggestion:

- `Module 10 - Organization and Multi-Site Operations`

---

## ACCEPTANCE CRITERIA

- Task 14 role/approval behavior remains intact.
- Mercury supports organization-aware and multi-site workflows in one application.
- Missions, alerts, dashboards, and connectors can be scoped by site.
- Operators only see and act within authorized scope.
- No duplicate mission, connector, or frontend applications are introduced.
- Existing Task 12 dashboard and current workspace shell remain intact.
- Existing API namespaces remain intact unless incrementally extended.
- Any new organization/site scoping is minimal, practical, and reusable by future audit/reporting/analytics tasks.
- No unnecessary database schema change is introduced.
- Site switching and scoped visibility are explicit, measurable, and safe.
- Decision-support remains advisory and never becomes autonomous execution.
