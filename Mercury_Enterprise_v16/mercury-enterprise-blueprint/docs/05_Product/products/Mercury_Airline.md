# Mercury Airline

| Field | Value |
|-------|--------|
| Product | Mercury Airline |
| Status | **Partial** |
| Family | Mercury AEOS |
| Companions | [README](README.md) · [Product Line Strategy](../Product_Line_Strategy.md) · [Digital Thread](../../04_Data/Digital_Thread.md) |

---

## 1. Purpose

Mercury Airline serves commercial, cargo, business-aviation and helicopter operators who need fleet airworthiness, maintenance control, and materials continuity on one Digital Thread.

---

## 2. Positioning

Mercury Airline is a named commercial and architectural product within the Mercury Aviation Enterprise Operating System. It does not ship a separate database or a divergent security model. It packages capabilities on **Mercury Core** so buyers recognize their operating role while the **Digital Thread** remains continuous.

---

## 3. Target users

- Maintenance control / MCC
- Fleet managers
- CAMO-contracting operators
- Flight ops (future deep integration)

---

## 4. Business capabilities

| Capability | Status |
|------------|--------|
| Aircraft registry and fleets | Delivered |
| Utilization and due list | Delivered |
| Planning and WP generation | Delivered |
| Logistics for operator stores | Delivered |
| Flight ops / OCC deep integration | Planned |
| Passenger ops systems | Out of scope |

---

## 5. Major entities

Aircraft, Fleet, Registration, Utilization, MaintenanceCheck, DeferredDefect, MEL item.

---

## 6. Relationships to the Digital Thread

Every mutation that affects configuration, airworthiness evidence, material, tooling, or certification must persist resolvable references (aircraft, task/work, publication revision, actor, organization). See [Digital Airworthiness Passport](../../10_Platform/Digital_Airworthiness_Passport.md) and [ADR-0002](../../08_Standards/ADR/ADR-0002-digital-thread-passport.md).

---

## 7. APIs

`/api/v1/fleet/*`, `/planning/*`, shared maintenance and logistics APIs.

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

Mercury Core; shares MRO execution modules when work is internal; Connect for OCC links.

---

## 11. Roadmap

Dispatch reliability cockpit; ETOPS/MEL UX depth; operator–MRO shared workspaces with audited sharing constructs.

---

## 12. Related documents

[Product Vision](../../01_Executive/Product_Vision.md) · [Editions](../Editions.md) · [Industries](../../03_Business/industries/Industries_Overview.md)
