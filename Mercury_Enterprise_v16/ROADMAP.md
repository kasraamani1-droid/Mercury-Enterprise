# Roadmap

Mercury ships as an incremental FastAPI + vanilla JS foundation. Items below are ordered by dependency on that architecture — not a commitment calendar.

## Delivered

| Tag / sprint | Focus |
|--------------|--------|
| V2.0 / package 16.0.0 | Command platform foundation, decisions, hardening |
| **v0.9.1** | Production security & infrastructure (HTTPS, headers, rate limits, Compose production profile) |
| **v0.9.2** | Enterprise observability & operations (logs, metrics, admin APIs, backup scripts) |

## Near term (additive)

1. **Shared session store** — Redis-backed sessions to allow multi-worker API processes  
2. **Metrics scrape gateway** — authenticated or network-isolated Prometheus access pattern  
3. **Deeper backup automation** — scheduled Compose jobs + restore drills in CI  
4. **Frontend admin views** — consume `/admin/*` without new SPA frameworks  

## Deferred platform expansion

Documented as a future multi-service shape (not current runtime):

- Mobile clients  
- Dedicated API gateway service  
- Object store / message queue  
- Full multi-tenant write scoping on every path  
- OIDC / SSO / MFA  
- Kubernetes HA under load  

## Explicit non-goals (current releases)

- Replacing vanilla JS with React/Vue/Angular/Next.js  
- Certified aviation/security operational use without independent validation  
- OAuth/Azure AD/SSO/MFA in the next patch unless separately scoped  

Track implementation truth in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).
