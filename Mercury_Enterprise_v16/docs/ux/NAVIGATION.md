# Mercury UX 2.0 — Navigation Model

## Primary chrome

```
┌──────── Sidebar ────────┬────────────── Main ──────────────────────┐
│ Brand                   │ Search trigger (Ctrl K) · Org · Site · ◐ │
│ Core                    ├──────────────────────────────────────────┤
│  Home / Command / …     │ Workspace tabs (open · close · switch)   │
│ Maintenance             ├──────────────────────────────────────────┤
│ Supply & Market         │ Active workspace content                 │
│ Platform                │                                          │
│ Operations Suite        │                                          │
│ Admin & Build           │                                          │
│ Favorite / Collapse     │                                          │
└─────────────────────────┴──────────────────────────────────────────┘
```

## Information architecture

1. **Core** — Home, Command, Aircraft, Fleet  
2. **Maintenance** — Planning, Work Orders, MRO Execution, Logbook, Engineering  
3. **Supply & Market** — Inventory, Logistics, Marketplace  
4. **Platform** — Digital Twin, Ops Twin, Authority, Organization, AI  
5. **Operations Suite** — Radar, Executive, History  
6. **Admin & Build** — Administration, Developer, Cloud, Integrations, Compliance  

## Shortcuts

| Action | Keys |
|--------|------|
| Command palette | `Ctrl/Cmd+K` or `Ctrl/Cmd+/` |
| Toggle theme | `Ctrl/Cmd+Shift+L` |
| Notifications | `Ctrl/Cmd+Shift+N` |
| Toggle sidebar / mobile nav | `[` |
| Go Home / Command / Aircraft / … | `G` then `H` / `C` / `A` / … |

## Persistence

- Favorites, pins, open tabs, recent workspaces → `localStorage` (`mercury.ux2.*`)
- Theme → `mercury.ux2.theme`
- Deep link → `#/workspaceId`

## Object workspaces (Task 27)

Area menus discover work. **Objects** are where work happens:

- Open from lists, Home, palette (`aircraft C-GMEA`), or `#/object/aircraft/{id}`
- Context tabs + shared rail (timeline, widgets, comments, AI)
- See [WORKSPACE_ENGINE_NAVIGATION.md](WORKSPACE_ENGINE_NAVIGATION.md)

## Legacy compatibility

Hidden `.product-tab` buttons remain so existing `enterprise.js` bindings continue to work. UX 2.0 sidebar is the canonical navigator.
