# Mercury Enterprise v16 — controlled pilot

These notes describe a **LAN or localhost** demonstration for an MRO/AMO/aircraft operator. They are not a production or internet-facing runbook.

| Document | Use |
| --- | --- |
| [DEPLOY.md](DEPLOY.md) | Start, stop, backup, restore, health |
| [DEMO.md](DEMO.md) | Closed-loop C-GMEA walk (SIM / demo) |
| [SECURITY.md](SECURITY.md) | Attack surface, demo accounts, OIDC blocker |

Default Compose publishes **only** the UI on host port `3000`. PostgreSQL and Redis stay on the Compose network.

Do not commit `.env`, database files, dumps, JWT/cookie secrets, or live demo passwords.
