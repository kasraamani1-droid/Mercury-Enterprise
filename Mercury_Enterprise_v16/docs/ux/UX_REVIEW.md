# Mercury Enterprise UX 2.0 — UX Review

**Date:** 2026-08-14  
**Scope:** Full frontend review + UX 2.0 shell (no new backend modules)  
**Stack:** Vanilla JS + CSS design system (no React/Vue)

## Current-state findings (pre-UX 2.0)

| Area | Finding | Severity |
|------|---------|----------|
| Navigation | Horizontal product tabs overcrowded (12+), no IA hierarchy | High |
| Discoverability | Programs 13–17 (Marketplace, Twin, Network, Plugins, Event Fabric) had **no UI** | High |
| Density | Command workspace is high-cognitive-load for daily MRO users | High |
| Speed | No command palette, no global jump, limited keyboard nav | Medium |
| Consistency | Mixed card/table/form patterns; Inter + emoji-heavy chrome | Medium |
| Theme | Dark-only; no light mode or tokenized theme bridge | Medium |
| Responsiveness | Partial breakpoints; topbar wraps poorly | Medium |
| Persistence | No favorites, pins, workspace tabs, or recent memory | Medium |
| Accessibility | Some labels present; focus rings inconsistent; emoji controls | Medium |

## UX 2.0 design intent

Mercury should feel like an **aviation enterprise operating system**: persistent left navigation, sparse chrome, fast keyboard access, workspace tabs, and clear domain homes — while preserving every existing operational module.

## Principles applied

- Minimal clicks to primary work (home → domain → action)
- Persistent sidebar + open workspace tabs
- Command palette (`Ctrl/Cmd+K`) and chord shortcuts (`G` then letter)
- Dark/light theme via design tokens
- Additive shell — legacy workspaces remain intact
- Honest empty/error states when APIs are unavailable

## Redesigned workspace map

| Workspace | Purpose | Backing |
|-----------|---------|---------|
| Landing Dashboard | Readiness KPIs, due list, activity | Health, dashboard, planning, notifications |
| Command Ops | Incidents / map / intel (legacy) | Existing command UI |
| Aircraft / Fleet | Registry & portfolio | `/fleet` |
| Maintenance Planning | Programs, forecast, hangar | Existing planning UI |
| Work Orders | Execution board summary | `/work-orders` + link to MRO |
| MRO Execution | Full Sprint 8 boards | Existing maintenance UI |
| Digital Logbook | Release / tech-log narrative | Bridged to MRO |
| Engineering | AD/SB/EO focus | Planning bridge |
| Inventory / Logistics | Stock + full logistics | Logistics UI |
| Marketplace | Product catalog | `/marketplace` |
| Digital Twin | Asset lifecycle viz | `/twin` (+ ops airport twin kept) |
| Authority / Organization | Portals | `/authority`, `/organizations` |
| AI Workspace | Advisory-only hub | Links to Copilot |
| Administration | Users/roles/audit | Existing admin |
| Developer Portal | Plugins + Event Fabric | `/plugins`, `/event-fabric` |

## Risks remaining

- Command map initializes while workspace may be hidden — invalidate on show
- New workspaces are **v1 shells** (list/overview), not full CRUD UIs
- Network / full logbook CRUD UIs still deferred
- Accessibility audit not complete (WCAG AA target next)

## Verdict

**UX foundation: GO for pilot.** Product-depth polish for Marketplace/Twin/Engineering remains **High priority** before Platform 1.0 GA marketing.
