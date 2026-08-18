# Mercury AEOS — Governance Recommendations

**Parent:** [MERCURY_AEOS_CONSTITUTION.md](MERCURY_AEOS_CONSTITUTION.md) Article X  
**Version:** 1.0 · 2026-08-14

---

## 1. Purpose

This document recommends **how Mercury governs** the Constitution, architecture decisions, product portfolio, and releases. It is operational guidance for leadership and leads.

---

## 2. Governance bodies (recommended)

| Body | Role | Cadence |
|------|------|---------|
| **Founder / CEO** | Mission, company pillars, Constitution Articles I–II, VI–VII | As needed |
| **CTO / Chief Enterprise Architect** | Architecture sovereignty, ADR approval, stack epoch | Weekly architecture |
| **CPO / Product** | Portfolio fit, fabric integration, UX outcomes | Biweekly product |
| **CISO / Security lead** | Security standards, release security gate | Per release |
| **Domain owners** | Fleet, MRO, Logistics, Marketplace, Twin, etc. | Continuous |

Start lightweight; formalize committees only when headcount requires it.

---

## 3. Decision records

| Instrument | Use when |
|------------|----------|
| **Constitution amendment** | Core principles, stack epoch, company pillars |
| **ADR** | Module boundary, event layer policy, major API break, security model |
| **RFC / design note** | Large features before coding |
| **APPLY_TASK / Program brief** | Scoped delivery; must not violate Constitution |

**Rule:** Code must not silently contradict Constitution. If it must, amend first.

### ADR hygiene

- One decision per ADR  
- Resolve duplicate early ADR numbers (0001–0006) in a cleanup program  
- Link ADRs from architecture docs and Constitution amendments  

---

## 4. Change control workflow

```
Idea → Product fit check (Article V–VI)
    → Architecture fit (Article VIII)
    → Security review if authz/tenant/secrets
    → ADR if boundary-changing
    → Implement (Engineering Standards)
    → Test + docs
    → Release gate
```

---

## 5. Release gates (recommended)

| Gate | Criteria |
|------|----------|
| **Internal demo** | Tests green; known simulated feeds labeled |
| **Pilot** | SECURITY.md controls; deploy docs; session/HA gaps documented |
| **Platform RC** | Fabric integration for shipped products; UX object open paths |
| **Platform 1.0 GA** | Constitution checklist + Program 18 readiness blockers closed |
| **Certified ops** | External validation only — out of band |

Never use “GA” marketing for simulated-only or non-isolated paths.

---

## 6. Domain ownership RACI (template)

| Domain | A (Accountable) | R (Responsible) | C | I |
|--------|-----------------|-----------------|---|---|
| Platform | CTO | Platform lead | Security, Product | All |
| Fleet / Aircraft | Domain owner | Backend + UX | Twin, MRO | Ops |
| MRO / Planning | Domain owner | Backend + UX | Logistics, Library | Ops |
| Marketplace | Product | Backend | Connect, Network | Finance |
| Twin / Fabric | Architect | Backend | All domains | Partners |
| Connect / Plugins | Platform | Backend | Partners | DevRel |

Fill names as org grows.

---

## 7. Compliance & ethics

- Non-certification posture remains default public claim  
- Partner data sharing only under org partnership + RBAC scopes  
- AI: human accountable; log advisory use  
- Marketplace: verification badges ≠ regulatory approval  

---

## 8. Future governance upgrades

When Mercury exceeds ~10 concurrent product streams or multi-region customers:

1. Architecture Review Board (ARB) monthly  
2. Security Review Board for external exposure  
3. Public developer terms for Marketplace / Connect  
4. Formal RFC mailing list or equivalent  
5. Versioned Constitution (semver) with deprecation windows  
6. Customer advisory council for hangar UX and authority readiness  

---

## 9. Measuring Constitution adherence

| Signal | Healthy | Unhealthy |
|--------|---------|-----------|
| New RBAC engines | 0 | ≥1 per year |
| ADRs for boundary changes | Present | Absent |
| Products missing fabric | Waived with date | Silent gaps |
| Duplicate event buses | Contracted dual-write | Unbounded growth |
| SPA framework proposals | Via amendment | Drive-by PR |

---

## 10. Immediate recommendations (post Task 36)

1. Link Constitution from README and onboarding.  
2. Require PR template checkbox: “Constitution Articles III–V reviewed.”  
3. Run ADR number cleanup.  
4. Map Program 18 readiness blockers to Constitution Articles (security, events, UX).  
5. Appoint domain owners in IMPLEMENTATION_STATUS or DOMAIN_MODEL.  

---

## Approval

Governance recommendations accompany Constitution v1.0. Adoption of boards and gates is at Founder/CTO discretion; the Constitution itself is binding upon ratification.
