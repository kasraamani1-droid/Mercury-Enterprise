# ADR-0015 — Mercury Digital Twin

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-08-14 |
| Related | ADR-0001, ADR-0002, ADR-0008, ADR-0011, ADR-0014 |

## Context

Mercury must represent the complete digital lifecycle of aviation assets without equating “digital twin” to a 3D model, and without duplicating Universal Data Fabric identity.

## Decision

1. Introduce `backend/app/twin/` as the Digital Twin product domain.
2. Bind every twin to a Fabric Digital Passport (passports never disappear).
3. Keep twin history append-only/immutable; ownership may change.
4. Store configuration baselines and architecture-only reliability snapshots on the twin.
5. Reuse Fabric relationships/events/thread for Digital Thread traversal.
6. Expose AI question metadata only — no LLM execution in this program.
7. Mark 3D visualization as future-ready metadata, not current runtime truth.

## Consequences

- Clear separation: Fabric = identity/thread substrate; Twin = lifecycle product
- Marketing must not claim 3D or live reliability/AI
- Future event-driven projections and visualization adapters plug into this model
