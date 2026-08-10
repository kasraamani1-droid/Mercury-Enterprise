# Mercury AI Engineering Workflow

Standard development workflow for the Mercury Enterprise Platform when work is driven by `APPLY_TASK_*.md` (or equivalent task definitions) and executed with AI-assisted engineering in Cursor.

This document is process guidance. Task-specific technical contracts live under `docs/design/` (for example `TASK16_IMPLEMENTATION_SPEC.md`).

---

## Engineering Gates

Every implementation must pass these gates in order. Do not skip gates. Do not start a later gate before the previous gate is complete (and approved where required).

### Gate 1 – Repository Analysis

- Read the entire repository (or all modules material to the task when the repo is large; prefer thorough coverage of backend, frontend, tests, and docs).
- Read all relevant `APPLY_TASK` files (current task and prerequisite tasks).
- Identify affected modules, dependencies, and reusable components.
- Output of this gate feeds planning and the implementation specification.

### Gate 2 – Specification

- Produce `docs/design/TASKxx_IMPLEMENTATION_SPEC.md`.
- List exact files, functions, APIs, schema changes, and UI changes.
- Include objective, scope, out of scope, test plan, rollback, risks, and validation checklist.
- **Wait for human approval before Gate 3.**

### Gate 3 – Checkpoint

- Create a git checkpoint branch and commit (recoverable pre-implementation baseline).
- Do not begin application-code implementation before this checkpoint exists.
- Do not commit secrets.

### Gate 4 – Implementation

- Implement only the approved scope in the specification.
- No architectural redesign unless explicitly requested and approved.
- Preserve backward compatibility (additive API/schema changes unless the approved spec says otherwise).
- Reuse existing components whenever possible.
- Ask before any deviation from the approved specification.

### Gate 5 – Validation

- Run backend tests (`pytest` for `backend/tests`).
- Run frontend checks (`node --check` on modified JS; compile checks as applicable).
- Run manual verification required by the specification.
- Fix failures before Gate 6.

### Gate 6 – Report

Produce an implementation report containing at least:

- files changed
- database changes
- APIs
- UI
- risks
- test results

### Gate 7 – Merge

- **Never merge without explicit human approval.**
- Do not push or force-push protected branches unless explicitly requested.

```text
Gate 1 Analysis → Gate 2 Spec → Approval → Gate 3 Checkpoint
    → Gate 4 Implementation → Gate 5 Validation → Gate 6 Report
    → Approval → Gate 7 Merge
```

---

## 1. Repository analysis

Before planning or coding:

1. Read the task file completely (`APPLY_TASK_N.md` or equivalent).
2. Inspect affected backend, frontend, schema, tests, and docs.
3. Map dependencies on prior tasks (auth, RBAC, site scoping, existing managers/services).
4. Search for reusable components, helpers, routes, and UI shells.
5. Identify constraints: vanilla JS frontend, FastAPI backend, existing API contracts, folder structure, routing, and UI layout.
6. Do not guess. If requirements or ownership are unclear, stop and ask.

---

## 2. Planning phase

1. Produce an implementation plan grounded in the actual repository (exact paths, symbols, endpoints).
2. Prefer additive changes over rewrites.
3. Call out risks, optional items, and recommended deferrals.
4. Explicitly list what is out of scope for the current task.
5. Do not write application code during planning unless the human explicitly requests otherwise.

---

## 3. Implementation specification requirements

For each non-trivial task, create a contract document before coding:

`docs/design/TASK{N}_IMPLEMENTATION_SPEC.md`

The specification must include at least:

1. Objective  
2. Scope  
3. Out of scope  
4. Files to modify  
5. Functions to modify  
6. Database schema changes  
7. API changes  
8. UI changes  
9. Test plan  
10. Rollback plan  
11. Risks  
12. Validation checklist  

Optional supporting structure (create folders as needed; do not invent filler docs):

```text
docs/
├── architecture/     # system docs when authored intentionally
├── design/           # task implementation specs (contracts)
├── decisions/        # ADRs when a decision must be recorded
└── runbooks/         # operational procedures when authored intentionally
```

Preserve existing documentation. Move nothing unless required. Do not invent architecture, ADR, or runbook content unless requested.

---

## 4. Approval process

1. Human reviews the task implementation specification.
2. Human approves the specification (or requests edits).
3. No application code changes before approval of the relevant specification (except creating the specification / workflow documents themselves when requested).
4. After approval, proceed in order: checkpoint commit → implement exactly per spec → test → implementation report.
5. Any deviation from the approved specification requires asking first and updating the specification when agreed.

---

## 5. Checkpoint commits

1. After specification approval and before implementation, create a checkpoint commit (or approved baseline commit on a task branch).
2. Checkpoint purpose: recoverable pre-implementation state.
3. Do not amend shared history or force-push protected branches unless explicitly requested.
4. Do not commit secrets (`.env`, credentials, keys).

---

## 6. Coding standards

1. Production-grade code only — no placeholders, TODO stubs, fake APIs, or mocked business logic unless explicitly requested.
2. Prefer reuse of existing modules, managers, routes, schemas, and UI shells.
3. Never duplicate functionality when an existing path can be extended safely.
4. Preserve backward compatibility of APIs unless the approved specification explicitly documents a breaking change (default: additive only).
5. Keep persistence/schema changes minimal and justified in the specification.
6. Match existing project style (naming, structure, error handling, session/RBAC patterns).
7. Never introduce React, Vue, Angular, Next.js, or other SPA frameworks unless explicitly requested as an architecture change.
8. Never redesign architecture unless requested.
9. Never expand scope beyond the approved specification.

---

## 7. Testing requirements

Before declaring a task complete:

1. Run available backend tests (`pytest` for `backend/tests`).
2. Run compile/syntax checks (`python -m compileall backend/app`, `node --check` on modified frontend JS).
3. Verify imports and critical existing flows still work (especially prior-task behaviors referenced by the current task).
4. Execute the task specification’s test plan and validation checklist.
5. Manual verification when the specification requires UI or role/site behavior checks.

---

## 8. Review checklist

- [ ] Work matches the approved `docs/design/TASK{N}_IMPLEMENTATION_SPEC.md`
- [ ] No unapproved scope expansion
- [ ] No architecture redesign unless requested
- [ ] Existing components reused where specified
- [ ] API changes additive / backward compatible unless explicitly approved otherwise
- [ ] Schema changes match the specification (no extras)
- [ ] Tests added/updated as specified and passing
- [ ] Frontend still loads; modified JS passes `node --check`
- [ ] Prior-task behaviors preserved where required
- [ ] Risks and rollback notes remain valid
- [ ] Implementation report produced

---

## 9. Merge policy

1. Do not merge without explicit human approval.
2. Do not push to remote unless explicitly requested.
3. Do not force-push `main` / `master`.
4. Merge only after tests pass and the implementation report has been reviewed.
5. Preferred flow: task branch → review → human approves merge → merge.

---

## 10. Definition of Done

A task is done only when all of the following are true:

1. Approved implementation specification exists under `docs/design/`.
2. Checkpoint commit was created before implementation (for implementation tasks).
3. Implementation matches the specification with no unapproved deviations.
4. Required tests and checks have been run and pass.
5. Validation checklist in the specification is satisfied.
6. Implementation report has been delivered.
7. Human has accepted the result (and approved merge separately, if merge is desired).

---

## 11. AI rules (mandatory)

1. **Never modify application code before approval** of the relevant implementation specification (documentation/workflow artifacts may be created when requested).
2. **Never expand scope** beyond the approved specification.
3. **Never redesign architecture** unless explicitly requested.
4. **Preserve backward compatibility** unless the approved specification says otherwise.
5. **Reuse existing components** whenever possible; prefer extension over replacement.
6. **Produce an implementation report after every task**, including at minimum:
   - files changed
   - database changes
   - APIs changed
   - UI changed
   - risks
   - test results
7. Stop and ask when requirements are ambiguous or a change would violate the specification.
8. Prefer additive, incremental, production-ready changes.
9. Do not invent documentation, fake integrations, or parallel subsystems.
10. Do not merge without explicit human approval.
11. Pass Engineering Gates 1–7 in order; never skip approval gates.

---

## 12. Standard task pipeline

The pipeline is the Engineering Gates sequence:

```text
Gate 1 – Repository Analysis
        ↓
Gate 2 – Specification (docs/design/TASKxx_IMPLEMENTATION_SPEC.md)
        ↓
Human approval
        ↓
Gate 3 – Checkpoint (branch + commit)
        ↓
Gate 4 – Implementation (approved scope only)
        ↓
Gate 5 – Validation (pytest, node checks, manual)
        ↓
Gate 6 – Implementation report
        ↓
Human merge approval
        ↓
Gate 7 – Merge
```

---

## Document control

| Field | Value |
|-------|-------|
| Path | `docs/AI_ENGINEERING_WORKFLOW.md` |
| Purpose | Standard Mercury AI-assisted engineering workflow |
| Related | `docs/design/TASK*_IMPLEMENTATION_SPEC.md` |
