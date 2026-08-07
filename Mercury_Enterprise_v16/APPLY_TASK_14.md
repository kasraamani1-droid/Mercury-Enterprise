# MERCURY ENTERPRISE V2.0

## MODULE 9 — RBAC AND HUMAN APPROVAL GATES
### TASK 14

OBJECTIVE

Build on the authentication and session foundation completed in Task 13 by adding role-based access control and explicit human approval gates.

This task separates operator, supervisor, administrator, and auditor capabilities.

---

## EXISTING FUNCTIONALITY TO REUSE

Reuse:

- authenticated session context from Task 13
- existing FastAPI backend and security structure
- existing write-protected backend actions
- existing DecisionEngine outputs
- existing frontend workspaces and session-aware shell

Do NOT create a second permission engine outside the current platform.

---

## EXACT SCOPE

Add authorization and approval controls around existing Mercury functions.

This task must remain incremental from Task 13.

It must extend the authentication and session foundation already established there rather than introducing a separate identity, policy, or approval platform.

Focus areas:

- role definitions and permission enforcement
- route/action protection
- explicit approval workflows for sensitive operational actions
- admin/auditor visibility boundaries
- frontend capability gating based on current role

This task must explicitly build on authenticated identity/session functionality from Task 13.

Task 14 should add authorization policy and approval behavior only.

It must not redesign the current Mercury dashboard, session model, frontend shell, or API architecture.

---

## ARCHITECTURE CONSTRAINTS

- Reuse the existing backend and frontend architecture.
- Extend current security patterns rather than replacing them.
- Do NOT create duplicate admin consoles or approval engines.
- Preserve existing API routes where possible.
- Keep authorization logic compatible with future organization/site scoping.
- Reuse the authentication/session design introduced by Task 13.
- Reuse the existing frontend application shell, admin workspace, and current operator/session surfaces where appropriate.
- Do NOT introduce duplicate role-management APIs, policy services, or dashboard variants.
- Prefer incremental protection of existing Mercury actions over creation of parallel protected workflows.

---

## BACKEND REQUIREMENTS

- Add role and permission enforcement inside the existing backend.
- Protect existing routes and sensitive flows incrementally.
- Reuse session identity from Task 13.
- Support human approval checkpoints for sensitive actions.
- Do NOT add autonomous decision execution.
- Preserve backward compatibility for existing routes wherever possible.
- Reuse existing write-protected actions and current backend request context.
- Do not introduce a separate authorization service when policy can be enforced inside the existing backend.
- No database schema change is required unless a minimal persistent role/approval model is proven necessary during implementation.

---

## FRONTEND REQUIREMENTS

- Show/hide or enable/disable controls based on role.
- Make approval-required actions explicit in the UI.
- Preserve current workspaces and navigation.
- Ensure unauthorized actions fail safely and visibly.
- Reuse the existing frontend shell and current admin/role simulation surfaces as migration points where practical.
- Do NOT create a second dashboard or separate approval application.
- Preserve Task 12 dashboard behavior and Task 13 authenticated session behavior.

---

## API REQUIREMENTS

- Preserve current endpoint structure where practical.
- Add authorization-aware responses and approval metadata where required.
- Avoid creating a parallel policy API unless absolutely necessary.
- Reuse the authenticated session context from Task 13.
- Any new approval-related endpoints must be minimal, incremental, and compatible with future organization/site scoping.
- Avoid duplicate role/approval API families when existing Mercury endpoints can be extended safely.

---

## HUMAN-CONTROL / SAFETY REQUIREMENTS

- Approval gates must require explicit human action.
- No recommendation may become executable without human review.
- Decision-support remains advisory even for privileged roles.
- All privileged actions must be attributable to a human user.
- No autonomous execution of operational actions.
- No automatic targeting, firing, interception, or weapon control.
- Authorization must restrict human actions, not automate them.

---

## TESTS

Add tests for:

- role enforcement
- unauthorized access rejection
- approval-required flows
- frontend role-based capability gating
- audit-friendly attribution of protected actions
- preservation of Task 13 authenticated session behavior
- safe failure behavior when an authenticated user lacks required permission

Task 13 authentication flows must continue to pass.
Existing dashboard and API behavior from Tasks 11 through 13 must remain passing unless intentionally expanded.

---

## VERIFICATION

- run backend tests
- run frontend checks/build
- verify role-based UI behavior manually
- verify approval flows require explicit human action
- verify authenticated users retain Task 13 session behavior after RBAC is added
- verify users with insufficient role cannot access protected backend actions
- verify the existing dashboard loads without duplication or alternative dashboard paths
- verify approval-required UI actions are visibly marked and do not auto-complete

---

## GIT INSTRUCTIONS

Before commit:

- `git status`
- `git diff --stat`

Commit message suggestion:

- `Module 9 - RBAC and Human Approval Gates`

---

## ACCEPTANCE CRITERIA

- Task 13 authenticated sessions remain functional.
- Distinct roles are enforced consistently across backend and frontend.
- Sensitive actions require explicit human approval where defined.
- Unauthorized users cannot access protected capabilities.
- No duplicate authorization or approval subsystem is introduced.
- Existing Task 12 dashboard behavior remains intact.
- Existing API routes remain usable unless explicitly protected by the new RBAC rules.
- Any new approval metadata or endpoints are minimal, incremental, and reusable by future organization/site work.
- No unnecessary database schema change is introduced.
- Decision-support remains advisory and never becomes autonomous execution.
