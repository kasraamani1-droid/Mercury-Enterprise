# MERCURY ENTERPRISE V2.0

## MODULE 7 — ADVANCED OPERATIONAL DASHBOARD
### TASK 12

OBJECTIVE

Build on the functionality completed in Task 11 by turning the existing Operator Dashboard Foundation into a more complete operator-facing command workspace.

This task is an incremental dashboard enhancement only.

Human operators remain in control.

Do NOT implement autonomous execution, automatic targeting, firing, interception, or weapon control.

---

## EXISTING FUNCTIONALITY TO REUSE

Reuse the existing Mercury architecture already present in the repository:

- existing FastAPI backend
- existing `GET /api/v1/dashboard/summary`
- existing health/readiness endpoints
- existing WebSocket support
- existing `frontend/js/api.js`
- existing `frontend/js/app.js`
- existing `frontend/index.html`
- existing Command workspace and dashboard cards
- existing AlertManager, TimelineManager, MissionService, FusionEngine, DecisionEngine, ConnectorManager

Do NOT create a second dashboard system.

---

## EXACT SCOPE

Extend the existing Command workspace with richer operator-facing information using current backend capabilities and small read-only API additions only where genuinely required.

Focus areas:

- operational summary refinement
- mission overview refinement
- recent alert visibility
- recent decision visibility
- connector and sensor status visibility
- timeline preview usability
- graceful degraded/offline rendering
- better use of existing WebSocket events

This task must explicitly build on Task 11 rather than replace it.

---

## ARCHITECTURE CONSTRAINTS

- Reuse the current HTML/CSS/JavaScript frontend.
- Reuse the existing centralized `frontend/js/api.js`.
- Reuse the current FastAPI backend and existing managers/engines.
- Do NOT create duplicate UI modules for dashboard, alerts, missions, or decisions.
- Do NOT create a second frontend application.
- Do NOT redesign the Mercury architecture.
- Prefer additive, incremental changes over rewrites.

---

## BACKEND REQUIREMENTS

- Preserve the existing dashboard summary API contract.
- Only add read-only endpoints if existing endpoints cannot expose already-available data.
- Reuse existing AlertManager, TimelineManager, MissionService, FusionEngine, DecisionEngine, and ConnectorManager.
- Do NOT introduce a new dashboard manager or reporting engine.
- Preserve backward compatibility for existing routes.

---

## FRONTEND REQUIREMENTS

- Improve the existing Command workspace rather than creating a new page.
- Surface recent alerts, recent decision-support activity, mission context, and connector status more clearly.
- Reuse existing cards, layout patterns, and styling direction.
- Extend existing loading, empty, error, and offline states.
- Continue using the centralized API layer and existing refresh patterns.
- Use current WebSocket support for incremental live updates where practical.

---

## API REQUIREMENTS

- Reuse `GET /api/v1/dashboard/summary`.
- Reuse existing incidents, alerts, health, and any current read-only mission/decision/timeline endpoints.
- If an additional endpoint is necessary, it must be read-only, incremental, and reuse existing services.
- Do NOT introduce a parallel dashboard API namespace.

---

## HUMAN-CONTROL / SAFETY REQUIREMENTS

- All decision outputs must remain advisory.
- Use wording such as `Recommended`, `Suggested`, and `Operator Review Required`.
- Do NOT expose any auto-execute workflow.
- Do NOT imply that backend recommendations were automatically acted upon.

---

## TESTS

Add or update tests for:

- dashboard rendering with live data
- degraded backend rendering
- offline rendering
- recent decision-support messaging
- connector/sensor status rendering
- API failure isolation so one failing section does not crash the full dashboard

Do NOT break existing backend tests.

---

## VERIFICATION

Run appropriate existing verification such as:

- backend tests if backend files changed
- JavaScript syntax/build checks already used by the repository
- manual browser validation of Command workspace rendering
- verification that WebSocket-driven updates do not break static refresh logic

---

## GIT INSTRUCTIONS

Before commit:

- `git status`
- `git diff --stat`

Commit message suggestion:

- `Module 7 - Advanced Operational Dashboard`

Do not commit until all verification passes.

---

## ACCEPTANCE CRITERIA

- Task 11 dashboard foundation remains intact.
- Existing dashboard summary API remains compatible.
- Command workspace shows richer operational context using existing Mercury systems.
- Backend connectivity loss degrades gracefully without full dashboard failure.
- Decision-support content is clearly advisory and operator-controlled.
- No duplicate dashboard architecture, API layer, or frontend application is introduced.

