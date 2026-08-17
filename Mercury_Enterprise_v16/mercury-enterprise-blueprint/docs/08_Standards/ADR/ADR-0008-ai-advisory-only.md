# ADR-0008 — AI is advisory only; it never certifies or releases

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-08-14 |
| Deciders | Lead architect, security lead, quality lead, product leadership |
| Affects | [AI Strategy](../../07_AI/AI_Strategy.md) · [Digital Twin](../../07_AI/Digital_Twin.md) · [Knowledge Graph](../../07_AI/Knowledge_Graph.md) · [Digital Signatures](../../06_Security/Digital_Signatures.md) · [RBAC](../../06_Security/RBAC.md) · [FAA](../../09_Regulations/FAA.md) |
| Supersedes | — |
| Superseded by | — |

---

## Context

AI can accelerate reliability analysis, shortage prediction, twin visualization, and document retrieval. In aviation, the same capability is dangerous if it:

- Auto-approves inspections
- Auto-releases aircraft
- Silently alters configuration or logbook evidence
- Presents probabilistic output as certified fact

Mercury already ships deterministic stubs and advisory surfaces. Market pressure will push for “autonomous maintenance.” Without a hard product law, a helpful model will eventually be wired into a certification path by accident.

Regulators and operators must always be able to answer: **which natural person held which authority when this aircraft was released?**

---

## Decision

**All Mercury AI capabilities are advisory.** AI may recommend, rank, summarize, forecast, or highlight — always with human-readable rationale and links into the Digital Thread. AI **must not**:

1. Create certification signatures or ACA releases  
2. Bypass RBAC, organization isolation, or fail-closed audit  
3. Mutate airworthiness evidence without an explicit, audited human action  
4. Be marketed as certified, approved, or authority-endorsed decision-making  

Any future exception requires a **new ADR**, a named human accountability model, and explicit operator procedure — not a feature flag.

Deterministic stubs used today are honest stubs: correct shape, no hidden model, labelled as such in [AI Strategy](../../07_AI/AI_Strategy.md).

---

## Consequences

### Positive

- Clear boundary for engineering, sales, and regulators.
- AI can still deliver large economic value on planning, logistics, and reliability without touching release authority.
- Signature and audit designs remain coherent ([ADR-0006](ADR-0006-audit-everywhere-fail-closed.md)).

### Negative / accepted costs

- Competitors may claim “AI-certified maintenance”; Mercury will refuse that language.
- Some workflows stay human-latency bound by design.
- Product must invest in explainability and evidence links, not only model accuracy.

### Rejected alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Auto-release with human override | Override culture fails under schedule pressure |
| Shadow AI that writes then asks | Contaminates evidence before review |
| Unlabelled generative assistants in certification UI | Creates authority ambiguity |

---

## Links

[AI Strategy](../../07_AI/AI_Strategy.md) · [Digital Signatures](../../06_Security/Digital_Signatures.md) · [ADR-0002](ADR-0002-digital-thread-passport.md) · [ADR-0006](ADR-0006-audit-everywhere-fail-closed.md) · [ICAO](../../09_Regulations/ICAO.md)
