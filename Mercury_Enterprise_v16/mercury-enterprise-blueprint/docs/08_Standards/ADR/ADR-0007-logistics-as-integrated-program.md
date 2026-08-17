# ADR-0007 — Logistics is an integrated program, not a bolt-on inventory module

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-08-13 |
| Deciders | Lead architect, supply-chain architect, MRO consultant, planning owner |
| Affects | [Domain Architecture](../../02_Architecture/Domain_Architecture.md) · [Airline](../../03_Business/Airline.md) · [MRO](../../03_Business/MRO.md) · [Digital Thread](../../04_Data/Digital_Thread.md) · [Product Family](../../05_Product/Product_Family.md) · [Suppliers & Logistics](../../03_Business/Suppliers_Logistics.md) |
| Supersedes | “Sprint 10 inventory candidates” as a separate afterthought |
| Superseded by | — |

---

## Context

Most aviation maintenance platforms treat stores as a satellite ERP: parts lists on job cards, then a disconnected inventory system, then spreadsheets for shortages. The Digital Thread breaks at the hangar door.

Mercury’s Sprint 9 planning already emitted `parts_plan_lines` and `tool_plan_lines` without live stock. Shipping a shallow inventory CRUD module would have frozen that gap into product identity.

Enterprise customers (airlines, MROs, CAMOs, lessors) require:

- Warehouse hierarchy and quarantine/receiving/hazmat semantics
- Part master, serialized/rotable units, consumable FIFO/FEFO
- Tool crib with calibration gates
- Material requests and full procurement (PR → RFQ → PO → receive → inspect → putaway)
- Automatic reservation and shortage raising when work packages are generated

That is a **program**, not a feature.

---

## Decision

**Implement Enterprise Logistics as Program B — one integrated `logistics` domain** bound to maintenance planning and execution:

1. Warehouse → stock ledger → tools → material requests → purchasing → vendors → shipping share one package and one audit posture.
2. Work-package generation **must** call material and tool planning bridges (reserve, shortage, purchase request, calibration gate).
3. Sprint 7 configuration (`component_catalog` / serialized install history) remains authoritative for aircraft configuration; logistics links optionally and does not replace install/remove APIs.
4. Stock truth is an **immutable movement ledger**; oversell fails closed.

---

## Consequences

### Positive

- Planning → stores → procurement becomes a continuous Digital Thread segment.
- Tool calibration can block unsafe issue/planning.
- Shortages are first-class, not tribal knowledge.
- AEOS positioning vs point MRO tools is proven on the hardest operational join.

### Negative / accepted costs

- Large domain surface area and a large service module.
- Nested commits between planning and logistics until a single-transaction bridge exists.
- Attachments/photos remain URI metadata until an object store lands.
- Mobile scan is API-ready; native hangar clients are future work.

### Rejected alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Inventory-only MVP | Would cement the planning/stores disconnect |
| External WMS integration only | Abandons Digital Thread ownership of material evidence |
| Duplicate part masters ignoring Sprint 7 | Creates configuration vs stores divergence |

---

## Links

[ADR-0001](ADR-0001-aeos-not-point-mro.md) · [ADR-0002](ADR-0002-digital-thread-passport.md) · [ADR-0006](ADR-0006-audit-everywhere-fail-closed.md) · [Product Family](../../05_Product/Product_Family.md) · [Suppliers & Logistics](../../03_Business/Suppliers_Logistics.md)
