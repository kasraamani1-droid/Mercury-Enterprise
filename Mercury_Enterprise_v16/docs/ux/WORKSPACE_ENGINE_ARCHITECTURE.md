# Mercury Workspace Engine — Architecture

**Task 27** · 2026-08-14 · Frontend-only (no new backend modules)

## Intent

Replace **page-oriented menus** with **context-oriented object workspaces**. Operators open an object (Aircraft, Work Order, Twin, …) and the shell assembles the tabs, timeline, widgets, and AI panel around that object.

```
Area navigation (UX 2.0)     Object sessions (Workspace Engine)
Home · Aircraft list · …  →  Aircraft C-GABC { Overview, Twin, WO, … }
```

## Package

```
frontend/js/workspace-engine/
  types.js      Object type catalog + tab definitions
  store.js      Sessions, pins, comments, widgets (localStorage)
  loaders.js    Soft API fetch + related bundles
  render.js     Header, tabs, main, rail HTML
  configuration.js  Aircraft configuration / components operator UI
  maintenance-ops.js  Work order, job card, logbook, planning-context operator UI
  engine.js     openObject / close / tab / mount
  index.js      Public exports
frontend/css/workspace-engine.css
```

Host surface: `#contextWorkspace` (area id `context`).

## Object model

```
Session {
  key: "aircraft:ac-…",
  type, id, label, tab
}
Record  ← API or synthetic context stub
Bundle  ← related WOs, due items, twin, timeline, …
```

Deep link: `#/object/{type}/{id}`

## Supported object types

Aircraft · Engine · APU · Work Order · Inspection · Finding · Component · Marketplace Listing · Supplier · Organization · Engineer · Planner · Technician · QA · Project · Digital Twin

Every type defines **context tabs** + **quick actions**. Every session mounts the **shared rail**: Timeline, Pinned widgets, Activity, Attachments, Comments, Notifications, Search, AI Panel.

## Aircraft example tabs

Overview · Configuration · Digital Twin · Maintenance · Work Orders · History · Logbook · Reliability · SB · AD · Components · Marketplace · Documents · AI Assistant

## Layering

| Layer | Role |
|-------|------|
| UX 2.0 shell | Area IA, command palette, theme |
| Workspace Engine | Object sessions + context chrome |
| Domain area pages | Lists / boards that *open* objects |
| Backend APIs | Unchanged contracts |

## Non-goals

- No React/SPA rewrite
- No new backend domain modules in this task
- Persona workspaces (Engineer/Planner/…) are context shells; full queues remain in Planning/MRO areas
