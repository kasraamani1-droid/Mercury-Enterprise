# MERCURY ENTERPRISE V2.0

## MODULE 8 — AUTHENTICATION AND SESSION FOUNDATION
### TASK 13

OBJECTIVE

Build on the functionality completed in Task 12 by adding enterprise-grade authentication and session foundations to the existing Mercury platform.

This task establishes identity and session handling, not full authorization policy.

Human operators remain in control.

---

## EXISTING FUNCTIONALITY TO REUSE

Reuse:

- existing FastAPI backend
- existing security package and API-key protection baseline
- existing frontend application shell and operator/session placeholder
- existing backend request context and configuration system
- existing WebSocket infrastructure

Do NOT create a separate identity subsystem outside the current backend.

---

## EXACT SCOPE

Add authentication and session support suitable for future enterprise access control.

This task must remain incremental from Task 12.

It should introduce identity and session foundations for the existing Mercury application without redesigning the current frontend or backend.

Focus areas:

- login/logout/session endpoints or equivalent session flow
- session-aware frontend bootstrapping
- authenticated operator identity display
- backend identity context propagation
- compatibility with future SSO/OIDC integration

This task must explicitly build on the operator-facing dashboard and shell completed by Task 12.

Task 13 should remain a single-application enhancement.

Do NOT add a separate authentication service, separate login frontend, or parallel session API family.

---

## ARCHITECTURE CONSTRAINTS

- Reuse the existing FastAPI application.
- Reuse the existing frontend application shell.
- Do NOT create a second auth service or separate frontend login app.
- Keep the design extensible for future SSO/OIDC.
- Prefer incremental additions inside current backend security/router structure.
- Reuse the existing request context, configuration, and security patterns already present in Mercury.
- Preserve the existing Command workspace, dashboard summary flow, and centralized `frontend/js/api.js` architecture.
- Avoid duplicate identity, session, or operator-profile subsystems.

---

## BACKEND REQUIREMENTS

- Add authentication/session functionality using the existing backend.
- Introduce only the minimum new backend components genuinely required for auth.
- Reuse existing config/logging/security patterns.
- Ensure request context can identify the current operator.
- Keep dashboard and existing read-only endpoints compatible.
- Reuse the current API-key protection baseline where practical as part of the migration path, not as a second long-term auth system.
- Prefer incremental extension of the existing backend security structure over introducing a separate identity engine.
- Preserve backward compatibility for existing non-auth API behavior where appropriate.
- No database schema change is required unless a minimal persistent identity/session store is proven necessary during implementation.

---

## FRONTEND REQUIREMENTS

- Add login/session-aware behavior to the existing frontend.
- Replace the current operator/session placeholder with real session information.
- Preserve the existing workspaces and Command UI.
- Handle expired or invalid sessions gracefully.
- Reuse the current HTML/CSS/JavaScript frontend rather than introducing a new client architecture.
- Reuse the current workspace shell and operator/session display locations already present in the UI.
- Preserve dashboard functionality completed in Tasks 11 and 12.

---

## API REQUIREMENTS

- Add only the minimum auth/session endpoints required.
- Preserve existing API behavior for non-auth flows where appropriate.
- Ensure future RBAC work can reuse the identity/session context from this task.
- Avoid creating duplicate login/session APIs when the existing backend can expose the required flows incrementally.
- Keep new endpoints compatible with the current frontend API usage pattern.

---

## HUMAN-CONTROL / SAFETY REQUIREMENTS

- Authentication must not introduce auto-approval or auto-execution behavior.
- Operator identity must be explicit for all human-driven actions.
- Unsafe actions must remain manual and operator-controlled.
- No autonomous execution of operational actions.
- No automatic targeting, firing, interception, or weapon control.

---

## TESTS

Add tests for:

- login success/failure
- session validity and expiry
- protected endpoint behavior
- frontend session initialization
- logout and session invalidation
- dashboard access after authentication is established
- graceful handling of expired or invalid sessions in the current shell

Existing dashboard behavior from Task 12 must continue to work for authenticated users.
Existing backend API tests must remain passing unless they are intentionally expanded for authenticated behavior.

---

## VERIFICATION

- run backend tests
- run existing frontend checks/build
- verify login, logout, refresh, and session persistence behavior
- verify current dashboard still loads after authentication is added
- verify existing Task 12 dashboard behavior still works after session initialization
- verify invalid or expired sessions fail safely without breaking the full frontend shell

---

## GIT INSTRUCTIONS

Before commit:

- `git status`
- `git diff --stat`

Commit message suggestion:

- `Module 8 - Authentication and Session Foundation`

---

## ACCEPTANCE CRITERIA

- Task 12 dashboard remains functional.
- Mercury supports authenticated operator sessions.
- Current operator identity is visible in the existing UI shell.
- Session expiration/failure is handled safely.
- No duplicate auth service or duplicate frontend application is introduced.
- Existing dashboard/API architecture remains intact.
- Any new auth/session endpoints are minimal, incremental, and reusable by future RBAC work.
- No unnecessary database schema change is introduced.
- Authentication remains separate from authorization; full RBAC is deferred to Task 14.
