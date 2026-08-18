# ADR-0018 — Ratify Mercury AEOS Constitution

- **Status:** Accepted
- **Date:** 2026-08-14
- **Deciders:** Founder / CTO / Chief Enterprise Architect (Task 36)

## Context

Mercury has grown from command/MRO modules into a multi-domain AEOS (platform, twin, marketplace, network, plugins, event fabric, UX shell, workspace engine). Engineering decisions were guided by scattered ADRs and program briefs without a single master policy.

## Decision

Ratify **Mercury AEOS Constitution v1.0** and companion standards under `docs/constitution/`:

- Core, engineering, user, product, and company principles are binding
- Architectural and product standards define mandatory reuse and fabric integration
- Governance recommendations define amendment and release-gate practice

Code and future programs must not contradict the Constitution without formal amendment + ADR.

## Consequences

- Onboarding and PR review cite Constitution Articles
- Stack epoch (FastAPI + vanilla JS) remains locked unless Constitution amended
- Platform-first / no duplicate engines becomes explicit review criteria
- Program 18 readiness and Platform 1.0 claims map to Constitutional gates

## Links

- [MERCURY_AEOS_CONSTITUTION.md](../../../../docs/constitution/MERCURY_AEOS_CONSTITUTION.md)
- [GOVERNANCE.md](../../../../docs/constitution/GOVERNANCE.md)
