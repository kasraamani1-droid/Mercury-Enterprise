# Mercury UX 2.0 — Component Inventory

## Design tokens (`css/design-system.css`)

| Token family | Examples |
|--------------|----------|
| Color | `--mx-bg`, `--mx-bg-panel`, `--mx-accent`, `--mx-ok/warn/danger` |
| Type | `--mx-font-sans` (IBM Plex Sans), `--mx-font-mono` |
| Space | `--mx-space-1` … `--mx-space-7` |
| Radius | `--mx-radius-sm/md/lg` |
| Layout | `--mx-sidebar-w`, `--mx-topbar-h`, `--mx-tabbar-h` |
| Theme | `[data-theme=dark|light]` |

## Layout / chrome

| Component | Selector / module | Status |
|-----------|-------------------|--------|
| App shell | `.ux2-app` | Shipped |
| Sidebar nav | `.ux2-sidebar`, `ux2/index.js` | Shipped |
| Top chrome | `.ux2-chrome` | Shipped |
| Workspace tabs | `.ux2-tabbar` | Shipped |
| Command palette | `.ux2-palette-*`, `command-palette.js` | Shipped |
| Theme toggle | `theme.js` | Shipped |
| Favorites / pins / recent | `prefs.js` | Shipped |

## Primitives

| Component | Class | Status |
|-----------|-------|--------|
| Card | `.mx-card` | Shipped |
| KPI | `.mx-kpi` | Shipped |
| Button | `.mx-btn`, `.mx-btn-ghost` | Shipped |
| Input / select | `.mx-input`, `.mx-select` | Shipped |
| Table | `.mx-table` | Shipped |
| Chip | `.mx-chip` | Shipped |
| Timeline | `.mx-timeline` | Shipped |
| Bar chart | `.mx-bar-chart` | Shipped (CSS) |
| Twin stage | `.mx-twin-stage` | Shipped (architecture viz) |
| Empty state | `.mx-empty` | Shipped |
| Grid | `.mx-grid-*` | Shipped |

## Icons

Phase 1 uses compact unicode glyphs in the nav registry (no icon font dependency).  
Phase 2: SVG sprite set (aircraft, hangar, stock, twin, shield) — see roadmap.

## Typography

- **UI:** IBM Plex Sans 400/500/600/700  
- **Mono:** IBM Plex Mono for IDs, timestamps, shortcuts  
- Scale: `.mx-display`, `.mx-title`, `.mx-subtitle`, `.mx-label`

## Workspace Engine (Task 27)

| Component | Module | Status |
|-----------|--------|--------|
| Object type catalog | `workspace-engine/types.js` | Shipped |
| Session store | `workspace-engine/store.js` | Shipped |
| Object shell / rail | `workspace-engine/render.js` + CSS | Shipped |
| openObject API | `workspace-engine/engine.js` | Shipped |
| Object tabs in UX2 tab bar | `ux2/index.js` | Shipped |

## Legacy components (retained)

Command map, incident list, telemetry cards, enterprise tables, logistics/planning/maintenance boards — unchanged functionally; visually inherit bridged CSS variables from the design system.
