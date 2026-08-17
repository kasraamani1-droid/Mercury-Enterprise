# Mercury Digital Airworthiness Passport

| Field | Value |
|-------|--------|
| Product | Mercury Digital Airworthiness Passport |
| Status | **Partial** |
| Family | Mercury AEOS |
| Companions | [README](README.md) · [Product Line Strategy](../Product_Line_Strategy.md) · [Digital Thread](../../04_Data/Digital_Thread.md) |

---

## 1. Purpose

The Digital Airworthiness Passport is the productized, transferable view of an aircraft's identity, configuration, life data, and airworthiness evidence on the Digital Thread.

---

## 2. Positioning

Mercury Digital Airworthiness Passport is a named commercial and architectural product within the Mercury Aviation Enterprise Operating System. It does not ship a separate database or a divergent security model. It packages capabilities on **Mercury Core** so buyers recognize their operating role while the **Digital Thread** remains continuous.

---

## 3. Target users

- Lessors and asset managers
- Operators at sale/lease return
- CAMO and quality leaders

---

## 4. Business capabilities

| Capability | Status |
|------------|--------|
| Underlying thread data | Delivered foundation |
| Productized passport UX/API pack | Planned |
| Cross-org transfer protocol | Planned |

---

## 5. Major entities

Logical view over Aircraft, SerializedComponent history, Certification events, Logbook, Publications, Logistics provenance.

---

## 6. Relationships to the Digital Thread

Every mutation that affects configuration, airworthiness evidence, material, tooling, or certification must persist resolvable references (aircraft, task/work, publication revision, actor, organization). See [Digital Airworthiness Passport](../../10_Platform/Digital_Airworthiness_Passport.md) and [ADR-0002](../../08_Standards/ADR/ADR-0002-digital-thread-passport.md).

---

## 7. APIs

Future `/api/v1/passport/*`; today assembled via domain APIs.

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

Core + all airworthiness domains; see Platform Passport architecture.

---

## 11. Roadmap

One-click evidence packs; lessor sharing grants; cryptographic sealing roadmap.

---

## 12. Related documents

[Product Vision](../../01_Executive/Product_Vision.md) · [Editions](../Editions.md) · [Industries](../../03_Business/industries/Industries_Overview.md)
