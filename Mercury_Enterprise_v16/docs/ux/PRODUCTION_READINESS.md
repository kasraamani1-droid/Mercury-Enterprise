# Mercury UX 2.0 — Production Readiness

## Status

| Audience | Status |
|----------|--------|
| Internal UX pilot / demo | **CONDITIONAL GO** |
| External customer GA | **NO GO** until UX 2.1 depth items land |
| Certified operational UI | **NO GO** (product posture unchanged) |

## Ready

- Additive vanilla JS shell; legacy modules preserved
- Theme tokens bridge legacy `--bg/--panel/--accent`
- Command palette + keyboard navigation
- Workspace deep links `#/id`
- Soft-fail API loaders (no hard crash on 403/empty)
- Design documentation under `docs/ux/`

## Gaps before UX GA

| ID | Gap | Priority |
|----|-----|----------|
| U1 | New workspaces are overview shells, not full task UIs | High |
| U2 | Leaflet map size when Command starts hidden | Medium (mitigated invalidateSize) |
| U3 | WCAG AA audit incomplete | High |
| U4 | Iconography still mixed unicode/legacy emoji | Medium |
| U5 | No automated **browser** tests (Playwright). API sequential smoke exists: `tests/test_rc1_e2e_smoke.py` | Medium |
| U6 | Notification center not fully bound to platform API | Medium |
| U7 | Network product UI missing | Medium |

## Test checklist (manual)

- [ ] Sign-in → Landing Dashboard KPIs load
- [ ] `Ctrl+K` jumps to Aircraft, Marketplace, Developer
- [ ] Theme toggle persists after reload
- [ ] Sidebar pins/favorites persist
- [ ] Command Ops map renders after leaving Home
- [ ] Planning / Maintenance / Logistics still refresh
- [ ] Mobile drawer opens under 980px
- [ ] Light theme readable on tables/forms

## Rollback

Disable by removing `initializeUx2()` from `app.js` and UX CSS links; legacy product tabs remain in DOM.
