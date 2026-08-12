# MERCURY ENTERPRISE V2.0

## MODULE 6 — OPERATOR DASHBOARD FOUNDATION
### TASK 11

OBJECTIVE

Build the first production-style frontend foundation for Mercury Enterprise.

The dashboard must consume the existing backend APIs and present operational information to a human operator.

Do not implement autonomous targeting, weapon control, firing, interception, or automatic operational execution.

Human operators remain responsible for all operational decisions.

---

## TECHNOLOGY

Use the existing frontend project.

Preferred stack:

- React
- TypeScript
- Vite if already present
- Existing CSS/design system where possible

Do NOT create a second frontend application if one already exists.

Before implementation, inspect the current frontend structure and reuse it.

---

## GOAL

Create the Mercury V2 operator dashboard shell containing:

- Application header
- Navigation
- System status
- Mission overview
- Alert overview
- Decision-support overview
- Sensor/Fusion status
- Timeline preview
- Backend connectivity status

This task is primarily frontend integration and architecture.

---

## 1. APPLICATION SHELL

Create or update the main layout.

Required navigation:

- Command
- Missions
- Tracks
- Alerts
- Decisions
- Timeline
- System

Header should display:

- Mercury Enterprise
- Version
- Backend connection status
- Current time
- Current operator/session placeholder

Do not implement authentication yet.

---

## 2. DASHBOARD HOME

Create a dashboard with summary cards:

- Active Missions
- Active Alerts
- Active Tracks
- Highest Threat Level
- Pending Human Decisions
- Backend Status

Do not hardcode operational numbers when the backend provides them.

Use safe fallback values when APIs are unavailable.

---

## 3. API CLIENT

Create a centralized frontend API layer.

Suggested structure:

frontend/src/api/

Files:

client.ts
missions.ts
alerts.ts
tracks.ts
decisions.ts
system.ts

Do not scatter fetch() calls throughout UI components.

Support:

- base API URL
- JSON parsing
- timeout
- error handling
- typed responses

Read API base URL from environment configuration where possible.

---

## 4. FRONTEND TYPES

Create:

frontend/src/types/

Suggested files:

mission.ts
alert.ts
track.ts
decision.ts
system.ts

Reuse backend field names where practical.

Do not invent conflicting domain models.

---

## 5. COMPONENT STRUCTURE

Create reusable components such as:

frontend/src/components/

AppShell
Navigation
StatusBadge
SummaryCard
SystemStatus
LoadingState
ErrorState
EmptyState

Do not duplicate components unnecessarily.

---

## 6. PAGES

Create or organize:

frontend/src/pages/

CommandPage
MissionsPage
TracksPage
AlertsPage
DecisionsPage
TimelinePage
SystemPage

Only the Command/Dashboard page needs full integration in this task.

Other pages may initially contain clean placeholders ready for future modules.

---

## 7. COMMAND PAGE

The Command page should display:

### Operational Summary
- Active missions
- Alerts
- Tracks
- Pending decisions

### Current Risk
Display:

- threat level
- threat score
- confidence

Use existing backend data only.

### Recent Alerts

Display recent alert records.

### Recent Decisions

Display decision-support recommendations.

Clearly label these as:

"Operator Decision Support"

Never imply that a recommendation was automatically executed.

### Mission Overview

Show:

- mission name
- status
- priority
- progress/objective information where available

### Timeline Preview

Show recent timeline entries.

---

## 8. BACKEND CONNECTIVITY

Add a backend health/status check.

Display:

- Connected
- Degraded
- Offline

The frontend must continue rendering even when backend requests fail.

Never crash the entire dashboard because one API is unavailable.

---

## 9. STATE MANAGEMENT

For this stage, prefer simple React state/hooks.

Do not add Redux or another heavy global state framework unless the existing frontend already uses one.

Keep the architecture easy to evolve later.

---

## 10. LOADING AND ERROR STATES

All backend-powered sections must support:

- Loading
- Success
- Empty
- Error

Do not leave blank sections.

---

## 11. RESPONSIVE DESIGN

Support:

- Desktop
- Laptop
- Tablet

Primary target is a desktop operations console.

Keep layouts usable at 1366x768 and above.

---

## 12. VISUAL STYLE

Maintain the existing Mercury dark operational style where possible.

Design goals:

- Professional
- High contrast
- Clean hierarchy
- Dense but readable
- Minimal decorative animation
- Clear status information

Avoid excessive visual effects.

---

## 13. SAFETY / HUMAN CONTROL

Any decision-support recommendation displayed by the frontend must explicitly remain advisory.

Use wording such as:

- Recommended
- Suggested
- Operator Review Required

Do not provide an "Auto Execute" capability.

Do not automatically trigger operational actions.

---

## 14. BACKEND

Do not rewrite backend business logic.

Only modify backend code if a very small read-only API endpoint is genuinely required to expose already-existing data.

If a backend change is necessary:

- explain it first
- keep it read-only
- reuse existing services
- add tests

Do not duplicate:
- EventBus
- Timeline
- Fusion
- Mission Management
- Alert Management
- Decision Engine
- Response Orchestration

---

## 15. TESTS

Add frontend tests where the existing project supports them.

At minimum verify:

- dashboard renders
- API failure does not crash application
- status cards render
- loading state renders
- empty state renders
- decision recommendations show human-review language

Do not break existing backend tests.

---

## 16. VERIFICATION

Inspect package.json and use the existing package manager.

Run the appropriate frontend commands such as:

npm install

npm run build

npm test

or equivalent existing scripts.

Also ensure backend regression tests remain healthy if backend files were modified.

---

## 17. GIT

Before commit:

git status
git diff --stat

Commit:

git add .

git commit -m "Module 6 - Operator Dashboard Foundation"

git push