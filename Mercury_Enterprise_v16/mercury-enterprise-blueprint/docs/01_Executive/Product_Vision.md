# Product Vision — Mercury AEOS Family

| Field | Value |
|-------|--------|
| Document | Product vision (architectural constitution) |
| Organization | Mercury Technologies |
| Status | Normative |
| Companions | [../../VISION.md](../../VISION.md) · [Company Vision](Vision.md) · [Product Line Strategy](../05_Product/Product_Line_Strategy.md) |

---

## 1. Scope

This document states the **product vision** for the Mercury Aviation Enterprise Operating System (AEOS) family: what products exist, what they share, and how they create customer outcomes without collapsing into a single undifferentiated “MRO app.”

Company vision (why Mercury exists) lives in [VISION.md](../../VISION.md) and [Vision.md](Vision.md). This document answers **what we build**.

---

## 2. Product vision statement

**Mercury products share one Core, one Digital Thread, and one Digital Airworthiness Passport — packaged so each industry role buys the cockpit it needs without fracturing the evidence chain.**

---

## 3. Design principles

| # | Principle | Implication |
|---|-----------|-------------|
| 1 | **Core before SKU** | Every product extends Mercury Core (identity, tenancy, audit, RBAC, APIs) |
| 2 | **Thread is not optional** | No product may create airworthiness-relevant records without Digital Thread links |
| 3 | **Honest packaging** | Delivered / Partial / Planned labelled in every product sheet |
| 4 | **Advisory AI** | Mercury AI never certifies or releases ([ADR-0008](../08_Standards/ADR/ADR-0008-ai-advisory-only.md)) |
| 5 | **API-first commerce** | Marketplace, Connect, and Developer Platform consume the same contracts as first-party UI |
| 6 | **Additive evolution** | New products extend modules; they do not rewrite the stack |

---

## 4. Outcomes by persona

| Persona | Product outcome |
|---------|-----------------|
| Technician | Mobile/job-card execution with parts and tools that resolve |
| Inspector / ACA | Certification workflow with SoD and publication binding |
| Planner | Forecast → work package → logistics reservation |
| Stores / purchasing | Integrated logistics, not a side ERP |
| CAMO engineer | Continuing airworthiness visibility across contracted work |
| OEM applicability engineer | Catalog and fleet feedback loops |
| Lessor technical | Passport transfer packs |
| Authority reviewer | Auditability when the operator elects to present evidence |
| Executive | Portfolio KPIs without shadow IT spreadsheets |
| Developer / integrator | Stable OpenAPI and future plugin model |

---

## 5. Product family (summary)

See full sheets under [../05_Product/products](../05_Product/products).

| Product | Intent | Status |
|---------|--------|--------|
| Mercury Core | Platform substrate | **Delivered** |
| Mercury MRO | Maintenance execution & materials | **Partial / strong** |
| Mercury Airline | Operator fleet & maintenance control | **Partial** |
| Mercury OEM | Manufacturer applicability & feedback | **Planned** (foundation Partial) |
| Mercury CAMO | Continuing airworthiness management | **Partial** |
| Mercury Marketplace | Ecosystem commerce & apps | **Planned** |
| Mercury Careers | Aviation talent marketplace | **Planned** |
| Mercury Academy | Training & competency | **Planned** |
| Mercury Authority | Oversight portal | **Planned** (audit Partial) |
| Mercury Executive | Executive command | **Partial** |
| Mercury AI | Advisory intelligence | **Partial** (stubs) |
| Mercury Connect | Integration hub | **Partial** |
| Mercury Mobile | Hangar / line mobile | **Planned** (scan API ready) |
| Mercury Developer Platform | Extensibility | **Planned** (OpenAPI today) |
| Mercury Digital Airworthiness Passport | Productized passport | **Partial → Planned productization** |
| Mercury Digital Twin | Twin platform | **Partial UI → Planned** |

---

## 6. Non-goals

- Replacing airline PSS / revenue management  
- Claiming Mercury itself is FAA/EASA/TCCA “certified software”  
- Autopilot certification or autonomous release  
- Rewriting the operator UI into a SPA framework ([ADR-0005](../08_Standards/ADR/ADR-0005-vanilla-js-fastapi-stack.md))

---

## 7. Success measures

| Measure | Signal |
|---------|--------|
| Thread completeness | Release → signatures → publication revision → parts/tools resolvable without spreadsheets |
| Time-to-evidence | Lease return / audit pack generation measured in hours, not weeks |
| Cross-role adoption | Same aircraft served by airline + MRO + CAMO without duplicate masters |
| API adoption | External systems consume `/api/v1` without UI scraping |

---

## 8. Related documents

[Product Line Strategy](../05_Product/Product_Line_Strategy.md) · [Future Vision 10-Year](Future_Vision_10_Year.md) · [Enterprise Architecture](../02_Architecture/Enterprise_Architecture.md) · [Digital Airworthiness Passport](../10_Platform/Digital_Airworthiness_Passport.md)
