# Mercury Technologies — Enterprise Blueprint

**Architectural constitution of Mercury Technologies**  
**Aviation Enterprise Operating System (AEOS)**  
**Single Source of Truth for every Mercury product**

| Field | Value |
|-------|--------|
| Nature | Documentation constitution — **not** application code |
| Governing ideas | One Digital Thread · One Digital Airworthiness Passport |
| Standards bar | Enterprise documentation quality comparable to leading enterprise platforms |
| Runtime conformity | Engineering repositories must conform to this blueprint and its ADRs |

---

## 1. Constitutional rule

If runtime code and this repository disagree, **this repository wins** until a superseding Architecture Decision Record is accepted.

---

## 2. Vision triad

| Document | Role |
|----------|------|
| [VISION.md](VISION.md) | Company vision |
| [docs/01_Executive/Product_Vision.md](docs/01_Executive/Product_Vision.md) | Product vision |
| [docs/01_Executive/Future_Vision_10_Year.md](docs/01_Executive/Future_Vision_10_Year.md) | 10-year future vision |

Also: [Mission](docs/01_Executive/Mission.md) · [Founders Letter](docs/01_Executive/Founders_Letter.md) · [Company Strategy](docs/01_Executive/Company_Strategy.md)

---

## 3. Repository map

```text
mercury-enterprise-blueprint/
├── README.md · LICENSE · VISION.md · ROADMAP.md
├── CONTRIBUTING.md · CHANGELOG.md · CODE_OF_CONDUCT.md · SECURITY.md
└── docs/
    ├── 01_Executive/     Vision, Mission, Product Vision, Strategy, 10-Year
    ├── 02_Architecture/  Enterprise, Domain, System Context, Technical
    ├── 03_Business/      OEM, Airline, MRO, CAMO, Authority, Leasing, Suppliers
    │   └── industries/   Industries overview (all sectors)
    ├── 04_Data/          Data Model, Master Data, Digital Thread, Knowledge Graph
    ├── 05_Product/       Family, Editions, Pricing, Line Strategy, products/*
    ├── 06_Security/      Identity, RBAC, Audit, Digital Signatures
    ├── 07_AI/            AI Strategy, Knowledge Graph, Digital Twin
    ├── 08_Standards/     API, UI, Coding, Naming, Release, Deploy, Quality, Test,
    │                     PRD, Database, Multi-Tenant, Marketplace, Supplier,
    │                     Authority, Certification, Logbook, Tasks, Library, OEM + ADR/
    ├── 09_Regulations/   FAA, Transport Canada, EASA, ICAO
    ├── 10_Platform/      DDD, Passport, Lifecycle, Marketplace, Zero Trust,
    │                     Plugin, AI Platform
    └── 11_Operations/    Operations index → standards
```

---

## 4. Constitution checklist (40)

| # | Topic | Location |
|---|-------|----------|
| 1 | Company Vision | [VISION.md](VISION.md) |
| 2 | Product Vision | [docs/01_Executive/Product_Vision.md](docs/01_Executive/Product_Vision.md) |
| 3 | Enterprise Architecture | [docs/02_Architecture/Enterprise_Architecture.md](docs/02_Architecture/Enterprise_Architecture.md) |
| 4 | Domain Driven Design | [docs/10_Platform/Domain_Driven_Design.md](docs/10_Platform/Domain_Driven_Design.md) |
| 5 | Business Domains | [docs/03_Business](docs/03_Business) |
| 6 | Product Line Strategy | [docs/05_Product/Product_Line_Strategy.md](docs/05_Product/Product_Line_Strategy.md) |
| 7 | Aviation Data Model | [docs/04_Data/Data_Model.md](docs/04_Data/Data_Model.md) |
| 8 | Digital Thread Architecture | [docs/04_Data/Digital_Thread.md](docs/04_Data/Digital_Thread.md) |
| 9 | Digital Airworthiness Passport | [docs/10_Platform/Digital_Airworthiness_Passport.md](docs/10_Platform/Digital_Airworthiness_Passport.md) |
| 10 | Marketplace Architecture | [docs/10_Platform/Marketplace_Architecture.md](docs/10_Platform/Marketplace_Architecture.md) |
| 11 | Authority Platform | [docs/05_Product/products/Mercury_Authority.md](docs/05_Product/products/Mercury_Authority.md) |
| 12 | AI Platform | [docs/10_Platform/AI_Platform.md](docs/10_Platform/AI_Platform.md) |
| 13 | Security Standards | [SECURITY.md](SECURITY.md) · [docs/06_Security](docs/06_Security) |
| 14 | Zero Trust Architecture | [docs/10_Platform/Zero_Trust_Architecture.md](docs/10_Platform/Zero_Trust_Architecture.md) |
| 15 | RBAC Standards | [docs/06_Security/RBAC.md](docs/06_Security/RBAC.md) |
| 16 | API Standards | [docs/08_Standards/API_Standards.md](docs/08_Standards/API_Standards.md) |
| 17 | UI/UX Standards | [docs/08_Standards/UI_Standards.md](docs/08_Standards/UI_Standards.md) |
| 18 | Coding Standards | [docs/08_Standards/Coding_Standards.md](docs/08_Standards/Coding_Standards.md) |
| 19 | Naming Standards | [docs/08_Standards/Naming_Standards.md](docs/08_Standards/Naming_Standards.md) |
| 20 | ADR Index | [docs/08_Standards/ADR/README.md](docs/08_Standards/ADR/README.md) |
| 21 | Roadmap | [ROADMAP.md](ROADMAP.md) |
| 22 | Release Strategy | [docs/08_Standards/Release_Strategy.md](docs/08_Standards/Release_Strategy.md) |
| 23 | Deployment Strategy | [docs/08_Standards/Deployment_Strategy.md](docs/08_Standards/Deployment_Strategy.md) |
| 24 | Quality Standards | [docs/08_Standards/Quality_Standards.md](docs/08_Standards/Quality_Standards.md) |
| 25 | Test Strategy | [docs/08_Standards/Test_Strategy.md](docs/08_Standards/Test_Strategy.md) |
| 26 | Product Requirement Standards | [docs/08_Standards/Product_Requirement_Standards.md](docs/08_Standards/Product_Requirement_Standards.md) |
| 27 | Database Standards | [docs/08_Standards/Database_Standards.md](docs/08_Standards/Database_Standards.md) |
| 28 | Multi-Tenant Standards | [docs/08_Standards/Multi_Tenant_Standards.md](docs/08_Standards/Multi_Tenant_Standards.md) |
| 29 | Plugin Architecture | [docs/10_Platform/Plugin_Architecture.md](docs/10_Platform/Plugin_Architecture.md) |
| 30 | Marketplace Standards | [docs/08_Standards/Marketplace_Standards.md](docs/08_Standards/Marketplace_Standards.md) |
| 31 | Supplier Verification | [docs/08_Standards/Supplier_Verification.md](docs/08_Standards/Supplier_Verification.md) |
| 32 | Authority Integration | [docs/08_Standards/Authority_Integration.md](docs/08_Standards/Authority_Integration.md) |
| 33 | Certification Workflow | [docs/08_Standards/Certification_Workflow.md](docs/08_Standards/Certification_Workflow.md) |
| 34 | Digital Signature Framework | [docs/06_Security/Digital_Signatures.md](docs/06_Security/Digital_Signatures.md) |
| 35 | Electronic Logbook Standards | [docs/08_Standards/Electronic_Logbook_Standards.md](docs/08_Standards/Electronic_Logbook_Standards.md) |
| 36 | Maintenance Task Standards | [docs/08_Standards/Maintenance_Task_Standards.md](docs/08_Standards/Maintenance_Task_Standards.md) |
| 37 | Technical Library Standards | [docs/08_Standards/Technical_Library_Standards.md](docs/08_Standards/Technical_Library_Standards.md) |
| 38 | OEM Integration Standards | [docs/08_Standards/OEM_Integration_Standards.md](docs/08_Standards/OEM_Integration_Standards.md) |
| 39 | Aircraft Lifecycle Model | [docs/10_Platform/Aircraft_Lifecycle_Model.md](docs/10_Platform/Aircraft_Lifecycle_Model.md) |
| 40 | Future Vision (10-Year) | [docs/01_Executive/Future_Vision_10_Year.md](docs/01_Executive/Future_Vision_10_Year.md) |

---

## 5. Mercury products

Index: [docs/05_Product/products/README.md](docs/05_Product/products/README.md)

Core · MRO · Airline · OEM · CAMO · Marketplace · Careers · Academy · Authority · Executive · AI · Connect · Mobile · Developer Platform · Digital Airworthiness Passport · Digital Twin

---

## 6. Supported industries

[docs/03_Business/industries/Industries_Overview.md](docs/03_Business/industries/Industries_Overview.md)

Airlines · Business Aviation · Cargo · Military *(future)* · Helicopters · UAV/Drone *(future)* · eVTOL *(future)* · Aircraft/Engine/Component Manufacturers · MROs · CAMOs · FBOs · Leasing · Authorities · Training Organizations

---

## 7. Core principles

Multi-tenant · Organization isolation · RBAC · Audit everywhere · API-first · AI-ready (advisory only) · Cloud-native · Event-ready · Modular · Enterprise scalable · Digital Thread · Digital Airworthiness Passport

---

## 8. Honesty

Delivered vs Partial vs Planned is labelled in product sheets. Mercury does **not** claim aviation authority product approval. Operators remain accountable for regulatory compliance.

---

## 9. Governance

[CONTRIBUTING.md](CONTRIBUTING.md) · [ADR Index](docs/08_Standards/ADR/README.md) · [SECURITY.md](SECURITY.md) · [LICENSE](LICENSE)
