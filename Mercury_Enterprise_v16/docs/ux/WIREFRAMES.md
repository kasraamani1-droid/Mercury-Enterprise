# Mercury UX 2.0 — Wireframes

ASCII wireframes for primary surfaces. Implementated shell matches these layouts.

## 1. Landing Dashboard

```
[Mercury]  Search…………… ⌘K     Org▾ Site▾  N  ◐
Tabs: Home · Command · Planning

Landing Dashboard
Mercury Operations Home          [Command Ops] [Planning]

┌ Platform ┐ ┌ Alerts ┐ ┌ Missions ┐ ┌ Decisions ┐
│ ok       │ │ 3      │ │ 1        │ │ 2         │
└──────────┘ └────────┘ └──────────┘ └───────────┘

┌ Due / forecast ──────────┐ ┌ Recent activity ─────┐
│ • A-CHK due 14d          │ │ • Notification …     │
│ • AD open                │ │ • Notification …     │
└──────────────────────────┘ └──────────────────────┘

[Aircraft] [Fleet] [Work Orders] [Marketplace] [Twin] [Developer]
```

## 2. Aircraft Workspace

```
Aircraft Registry                         [Fleet view]
┌─────────────────────────────────────────────────────┐
│ Registration │ Model │ Status │ Operator │ ID       │
│ C-GMEA       │ 737   │ IN_SVC │ Demo Air │ ac-…     │
└─────────────────────────────────────────────────────┘
Context: row click → future detail drawer (roadmap)
```

## 3. Maintenance Planning (existing + shell)

```
Sidebar: Planning active
Page heading + Refresh
KPI strip
Grid: Aircraft status | Due list | Programs | Checks | Defects | Hangar | Forecast
```

## 4. Work Orders

```
Execution Board                    [Open MRO Execution]
Package chips: [WP-1 · open] [WP-2 · in_work]
Table: Order | Package | Status | Aircraft | Priority
```

## 5. Digital Twin (asset)

```
Asset Lifecycle Twin                 [Ops Airport Twin]
┌────────────── Twin stage ──────────────────────────┐
│  HUD chips · orbit · core node · passport/config   │
└────────────────────────────────────────────────────┘
Table of twins: Name | UUID | Lifecycle | Entity
```

## 6. Marketplace

```
Aviation Parts Marketplace
┌ Product card ┐ ┌ Product card ┐ ┌ Product card ┐
│ Category     │ │ …            │ │ …            │
│ Name         │ │              │ │              │
│ Status chip  │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

## 7. Command palette

```
┌────────────────────────────────────────────┐
│ Go to workspace, search, or run a command… │
├────────────────────────────────────────────┤
│ ✈ Aircraft Workspace              Core     │
│ ◈ Marketplace                  Supply      │
│ ◐ Toggle light / dark theme   Appearance   │
└────────────────────────────────────────────┘
```

## 8. Mobile (&lt;980px)

```
☰  Search…          ◐
[drawer sidebar overlay]
Full-width workspace
```
