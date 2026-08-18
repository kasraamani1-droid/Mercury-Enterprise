# Mercury AEOS — Product Standards

**Parent:** [MERCURY_AEOS_CONSTITUTION.md](MERCURY_AEOS_CONSTITUTION.md) Articles IV–VI  
**Version:** 1.0 · 2026-08-14

---

## 1. Product definition

A **Mercury product** is a coherent capability set (e.g. Marketplace, Digital Twin, Network, Planning) that:

- Ships under the AEOS brand  
- Consumes platform services  
- Exposes APIs  
- Integrates into the fabric listed below  

A feature that cannot meet these standards is a **spike** or **prototype**, not a product.

---

## 2. Mandatory fabric integration

Every product checklist:

| Fabric | Minimum bar |
|--------|-------------|
| **Identity** | Session/org context; no side login |
| **Digital Twin** | Link or readiness path for lifecycle assets |
| **Enterprise Search** | Indexable metadata or search documents |
| **Notifications** | Events users must know about |
| **Workflow Engine** | Status changes prefer definitions/bridge |
| **Marketplace** | Commercial exchange uses marketplace domain (or explicit non-commerce) |
| **AI** | Advisory metadata; human control labeled |
| **Analytics** | Measurable KPIs/events for ops/executive |
| **Event Fabric** | Durable publish for integration-grade changes |

Products that “skip” fabric for speed must file an ADR with a sunset date.

---

## 3. Product portfolio alignment

| Company pillar | Product expectation |
|----------------|---------------------|
| Enterprise Software | Org-isolated, auditable operational modules |
| Developer Platform | OpenAPI, plugins, Connect, Event Fabric, docs |
| Marketplace | Sellers/products/orders; payments explicitly configured |
| Integration Platform | Connectors as contracts first, live adapters second |
| Digital Aviation Network | Partnership-gated collaboration — not social feed |
| AI Platform | Copilot/advisory; explainability |
| Digital Twin Platform | UUID twins + passport — not 3D-first marketing |
| Knowledge Platform | Library, search, graph-ready relations |

---

## 4. UX product standards

Aligned with User Law (Constitution Article IV):

1. Object-centric Workspace Engine for entity work  
2. Area boards for queues and planning  
3. Command palette and keyboard access  
4. Hangar flows: large tap targets, offline queue, minimal typing  
5. Honest empty states and non-certification labels where required  

---

## 5. Release & messaging standards

| Claim | Allowed when |
|-------|--------------|
| “API ready” | Tests + OpenAPI + RBAC |
| “Production pilot” | Security baseline + deploy docs + known gaps listed |
| “Platform 1.0 GA” | Constitution release gate + readiness checklist closed |
| “Certified / approved” | **Never** without external authority process |
| “Live OEM integration” | Connect binding + non-simulated adapter |

Disclaimers in README and product surfaces remain until certification posture changes.

---

## 6. Product DoD (Definition of Done)

- Fabric checklist complete or ADR waiver  
- Engineering Standards E1–E10  
- UX entry points (list → object workspace or documented exception)  
- CHANGELOG + architecture blurb  
- Permissions named and seeded  
- Seed data or migration for demo path  

---

## 7. Anti-patterns

- “Shadow platform” inside a product  
- UI without API  
- API without permission  
- Permission without audit on sensitive mutation  
- Twin marketed as 3D when only registry exists  
- Network marketed as social media  
- AI marketed as autonomous release authority  
