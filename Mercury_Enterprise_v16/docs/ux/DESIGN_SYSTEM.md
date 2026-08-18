# Mercury Design System (UX 2.0)

## Foundations

- **Fonts:** IBM Plex Sans + IBM Plex Mono  
- **Default theme:** Dark aviation console; Light enterprise admin  
- **Accent:** Mercury blue `#1f8fff` (dark) / `#0b6bcb` (light)  
- **Spacing:** 4px base unit  
- **Radius:** 6 / 10 / 14  

## Usage

```html
<link rel="stylesheet" href="css/design-system.css">
<link rel="stylesheet" href="css/ux2-shell.css">
```

```js
import { initializeUx2 } from "./ux2/index.js";
initializeUx2({ onNavigate: (id) => showWorkspace(id) });
```

## Do

- Prefer `.mx-*` primitives for new surfaces  
- Keep domain logic in existing `*Workspace` modules  
- Fail soft when APIs return empty/403  

## Don’t

- Introduce SPA frameworks  
- Duplicate RBAC or API clients outside `api.js` / `ux2/api.js`  
- Market Twin viz as a 3D product  
