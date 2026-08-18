# Workspace Engine — Navigation

## How users open objects

1. **Click a row** in Aircraft / Work Orders / Marketplace / Twin / Organization lists  
2. **Command palette** (`Ctrl/Cmd+K`) — type `aircraft C-GMEA` or search  
3. **Home** — “Open Aircraft C-GMEA”  
4. **Sidebar** — Pinned objects / Recent objects  
5. **Deep link** — `#/object/aircraft/ac-c-gmea`  
6. **Related chips** inside an open workspace (e.g. related work orders, job cards, logbook)

Job cards open as `jobCard:{id}` object sessions (not a separate area page). `data-we-tab` on `data-we-open` jumps to a specific object tab (for example aircraft logbook) while keeping other object sessions.

## Tab bar model

```
[ Home ] [ Aircraft list ] … │ [ ✈ C-GMEA ] [ ☰ WO-… ]
   area tabs (UX2)              object sessions (Engine)
```

Closing an object tab closes that session. Closing the last object returns to Home (or empty Open Objects).

## Inside an object workspace

```
┌ Type · Label · Status · Quick actions · Close ┐
├ Overview │ Config │ Twin │ Maintenance │ …     ┤
├─────────────────────┬──────────────────────────┤
│ Tab content         │ Rail                     │
│                     │ Widgets · Timeline       │
│                     │ Attachments · Comments   │
│                     │ Search · AI Panel        │
└─────────────────────┴──────────────────────────┘
```

## Area “Open Objects”

Sidebar item **Open Objects** (`G` then `X`) shows the active object session, or an empty state with guidance when none are open.

## Persistence

| Key | Purpose |
|-----|---------|
| `mercury.we.sessions` | Open object sessions |
| `mercury.we.active` | Active session key |
| `mercury.we.recentObjects` | Recents |
| `mercury.we.pinnedObjects` | Pins |
| `mercury.we.widgets` | Per-session pinned widgets |
| `mercury.we.comments` | Local comments |

## Relationship to UX 2.0 menus

Area menus remain for **discovery and boards**. Object workspaces are for **doing work on a thing**. Lists should open objects; they should not be the only place work happens.
