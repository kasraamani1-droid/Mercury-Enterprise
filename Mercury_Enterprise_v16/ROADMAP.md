# Roadmap

Mercury ships as an incremental FastAPI + vanilla JS foundation. Items below are ordered by dependency on that architecture — not a commitment calendar.

## Delivered

| Tag / sprint | Focus |
|--------------|--------|
| V2.0 / package 16.0.0 | Command platform foundation, decisions, hardening |
| **v0.9.1** | Production security & infrastructure (HTTPS, headers, rate limits, Compose production profile) |
| **v0.9.2** | Enterprise observability & operations (logs, metrics, admin APIs, backup scripts) |
| **Sprint 5** | Enterprise organizations & multi-tenancy (companies, sites, departments, teams, memberships) |
| **Sprint 6** | Aircraft registry & fleet management (manufacturers, models, aircraft, registrations, fleets) |
| **Sprint 7** | Aircraft components & configuration (ATA, catalog, serialized parts, install history) |
| **Sprint 7b** | Publications, technical library, personnel, maintenance task engine, certification, signatures, tech logbook, AI stubs |

## Near term (additive) — Sprint 8 candidates

1. **Frontend admin views** — personnel, library, certification, and logbook UIs (vanilla JS)  
2. **Permission overrides** — individual / ATA / fleet-scoped grants beyond session roles  
3. **PKI / smart-card adapters** — real signature providers behind existing method flags  
4. **Authorized document ingestion** — object-store upload + licensed OEM pipelines (still not AI/RAG)  
5. **Work orders / MPD planning engine** — schedule, due lists, compliance findings  
6. **Shared session store** — Redis-backed sessions for multi-worker API  
7. **Directory sync / IdP** — unify org users with operator store / OIDC

## Deferred platform expansion

Documented as a future multi-service shape (not current runtime):

- Mobile clients  
- Dedicated API gateway service  
- Object store / message queue  
- Full multi-tenant write scoping on every path (org APIs + session isolation shipped; extend remaining engines as needed)  
- OIDC / SSO / MFA  
- Kubernetes HA under load  

## Explicit non-goals (current releases)

- Replacing vanilla JS with React/Vue/Angular/Next.js  
- Certified aviation/security operational use without independent validation  
- OAuth/Azure AD/SSO/MFA in the next patch unless separately scoped  

Track implementation truth in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).
