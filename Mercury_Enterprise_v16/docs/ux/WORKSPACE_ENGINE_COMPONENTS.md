# Workspace Engine — Frontend Components

## CSS

| Class | Role |
|-------|------|
| `.we-shell` | Object workspace frame |
| `.we-header` | Type badge, title, status, actions |
| `.we-tabs` / `.we-tab` | Context tabs |
| `.we-body` / `.we-main` / `.we-rail` | Content + right rail |
| `.we-widget` | Pinned KPI widgets |
| `.we-json` | Summary inspector |
| `.we-comment*` | Comments thread + form |
| `.we-ai-panel` | Advisory AI rail |
| `.ux2-tab.we-object-tab` | Object session in global tab bar |

## JS API

```js
import { openObject, closeObject, focusSession, listObjectTypes } from "./workspace-engine/index.js";

await openObject("aircraft", "ac-c-gmea", { label: "C-GMEA", tab: "overview" });
```

| Export | Description |
|--------|-------------|
| `openObject(type, id, opts)` | Open / focus object session |
| `closeObject(key)` | Close session |
| `focusSession(key)` | Focus existing session |
| `getOpenObjectSessions()` | Open sessions list |
| `listObjectTypes()` | Catalog |
| `searchObjects(q)` | Soft search helper |
| `initializeWorkspaceEngine({ onAreaNavigate, onSessionsChanged })` | Boot |

## Markup hooks

| Attribute | Effect |
|-----------|--------|
| `data-we-open="aircraft:id"` | Open object on click |
| `data-we-label` | Optional display label |
| `data-we-tab` | Internal tab switch |
| `data-we-action` | Quick action |

## Extending a type

1. Add entry to `OBJECT_TYPES` in `types.js` (tabs + quickActions + resolveLabel)  
2. Optionally extend `loadObjectRecord` / `loadRelatedBundle` in `loaders.js`  
3. Optionally specialize `renderMainTab` for new tab ids  

No backend module required for shell registration.
