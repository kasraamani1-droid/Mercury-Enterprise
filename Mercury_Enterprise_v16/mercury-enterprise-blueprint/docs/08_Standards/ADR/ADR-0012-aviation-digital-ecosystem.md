# ADR-0012 — Aviation Digital Ecosystem + Mercury Connect

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-08-14 |
| Related | ADR-0001, ADR-0009, ADR-0010, ADR-0011 |

## Context

Mercury must serve airlines, bizav, MRO, CAMO, OEM, suppliers, repair stations, authorities, training, careers, and marketplace on one AEOS while preserving tenant isolation and data ownership — without claiming regulatory approval.

## Decision

1. Introduce **Ecosystem** registry (definitions, capabilities, enrollments).
2. Introduce **Mercury Connect** connector catalog + org bindings (vault refs only).
3. Reuse **Universal Data Fabric** for digital identities and immutable timeline.
4. Map capabilities to existing domain packages and fabric entity types.
5. Authority ecosystem is **architecture readiness only**.

## Consequences

- Clear product portfolio alignment to stakeholder ecosystems
- Incremental capability readiness (ready/partial/planned)
- Connect becomes the single integration facade for future adapters
- Marketing/compliance must respect planned vs ready and authority disclaimer
