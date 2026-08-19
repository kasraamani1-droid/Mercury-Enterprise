# Mercury Enterprise v16 — controlled pilot

These notes describe a **LAN or localhost** demonstration for an MRO/AMO/aircraft operator. They are not a production or internet-facing runbook.

| Document | Use |
| --- | --- |
| [DEPLOY.md](DEPLOY.md) | Start, stop, backup, restore, health |
| [DEMO.md](DEMO.md) | Closed-loop C-GMEA walk (SIM / demo) |
| [SECURITY.md](SECURITY.md) | Attack surface, demo accounts, OIDC activation |
| [PRODUCTION.md](PRODUCTION.md) | Internet TLS, OIDC, backup encryption, remaining external steps |
| [ACTIVATION.md](ACTIVATION.md) | Cycle 8 A/B/C checklist + OWNER ACTION REQUIRED (DNS, IdP, certs) |
| [OPERATORS.md](OPERATORS.md) | Named `org_users` bound to IdP `sub` |
| [ROLLBACK.md](ROLLBACK.md) | Stop vs down -v, dump restore, config rollback |

Default Compose publishes **only** the UI on host port `3000`. PostgreSQL and Redis stay on the Compose network.

Do not commit `.env`, database files, dumps, JWT/cookie secrets, or live demo passwords.
