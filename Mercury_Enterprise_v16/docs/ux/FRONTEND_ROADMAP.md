# Mercury UX 2.0 — Frontend Roadmap

## Shipped (Task 19 + Task 27)

- Design system tokens + light/dark theme
- App shell: sidebar IA, tabs, search trigger, command palette, shortcuts
- Landing Dashboard
- Aircraft, Fleet, Work Orders, Logbook, Engineering, Inventory shells
- Marketplace, Asset Twin, Authority, Organization, AI, Developer portals
- Workspace Engine — object-centric sessions (tabs, rail, AI, deep links)
- Aircraft Workspace Engine Configuration/Components (PR #9)
- Maintenance operations integration — WO / job card / logbook (PR #10)
- Enterprise logistics operator integration — stores desk, materials bridge, part/MR/PO/tool objects
- Maintenance planning operator integration — due/forecast desk, AD/SB/EO, MEL/defects, selected-check WP generation

## Near term (UX 2.1)

1. Marketplace quote/cart already in UI; orders/payments remain deferred
2. Twin detail: history + configuration panels
3. SVG icon set; remove remaining emoji chrome in legacy topbar
4. Focus-visible audit + skip links
5. Network collaboration workspace (API Program 14)

## Mid term (UX 2.2)

1. Global pinned objects (aircraft, WO, twin) across sessions (server-backed)
2. Notification center bound to `/platform/notifications` realtime
3. Chart library (lightweight canvas) for planning forecast
4. Offline hangar mode polish for MRO boards
5. Persona layouts (Technician / Planner / ACA)

## Explicit non-goals

- React/Vue/Angular migration
- Replacing FastAPI contracts
- Claiming certified flight/maintenance UI approval
