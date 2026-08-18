# Mercury MRO

| Field | Value |
|-------|--------|
| Product | Mercury MRO |
| Status | **Partial** |
| Family | Mercury AEOS |
| Companions | [README](README.md) · [Product Line Strategy](../Product_Line_Strategy.md) · [Digital Thread](../../04_Data/Digital_Thread.md) |

---

## 1. Purpose

Mercury MRO packages maintenance execution, planning, logistics, personnel certification, and technical library workflows for maintenance, repair and overhaul organizations and operator maintenance departments.

---

## 2. Positioning

Mercury MRO is a named commercial and architectural product within the Mercury Aviation Enterprise Operating System. It does not ship a separate database or a divergent security model. It packages capabilities on **Mercury Core** so buyers recognize their operating role while the **Digital Thread** remains continuous.

---

## 3. Target users

- Technicians, inspectors, II, ACA
- Supervisors, planners, stores, purchasing
- Quality and reliability

---

## 4. Business capabilities

| Capability | Status |
|------------|--------|
| Work packages / orders / job cards | Delivered |
| Certification / double inspection / ACA | Delivered |
| Maintenance planning / MPD / AD-SB-EO | Delivered |
| Logistics Program B | Delivered |
| Tool crib and calibration | Delivered |
| Shop-visit financials | Planned |

---

## 5. Major entities

WorkPackage, WorkOrder, JobCard, MaintenanceTask, Publication revision, StockMovement, Tool, MaterialRequest, PurchaseOrder.

---

## 6. Relationships to the Digital Thread

Every mutation that affects configuration, airworthiness evidence, material, tooling, or certification must persist resolvable references (aircraft, task/work, publication revision, actor, organization). See [Digital Airworthiness Passport](../../10_Platform/Digital_Airworthiness_Passport.md) and [ADR-0002](../../08_Standards/ADR/ADR-0002-digital-thread-passport.md).

---

## 7. APIs

`/api/v1/work-orders/*`, `/planning/*`, `/logistics/*`, `/maintenance/*`, `/personnel/*`, `/library/*`.

All APIs follow [API Standards](../../08_Standards/API_Standards.md) and organization isolation ([Multi-Tenant Standards](../../08_Standards/Multi_Tenant_Standards.md)).

---

## 8. Security

| Control | Application |
|---------|-------------|
| RBAC | Product permissions subset of the central catalogue |
| Org isolation | Service-layer enforcement on every query |
| Audit | Fail-closed on safety-critical mutations |
| AI | Advisory only if AI surfaces are included |

See [RBAC](../../06_Security/RBAC.md) · [Audit](../../06_Security/Audit.md) · [Zero Trust](../../10_Platform/Zero_Trust_Architecture.md).

---

## 9. Workflows

```mermaid
flowchart LR
  User[Authorized user] --> API[Enterprise API]
  API --> Svc[Domain service]
  Svc --> Thread[Digital Thread write]
  Svc --> Audit[Audit record]
```

Product-specific workflows are detailed in domain standards under `docs/08_Standards` and business views under `docs/03_Business`.

---

## 10. Dependencies

Requires Mercury Core. Aligns with Airline and CAMO on shared aircraft thread. Passport productizes evidence export.

---

## 11. Roadmap

Mobile hangar client; deeper shop hierarchy; single-transaction certify bridges; Marketplace parts sourcing.

---

## 12. Related documents

[Product Vision](../../01_Executive/Product_Vision.md) · [Editions](../Editions.md) · [Industries](../../03_Business/industries/Industries_Overview.md)
