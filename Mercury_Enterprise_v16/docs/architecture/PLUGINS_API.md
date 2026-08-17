# Plugin Platform API

Base: `/api/v1/plugins`

| Area | Methods | Paths |
|------|---------|-------|
| Overview | GET | `/overview` |
| Catalog | GET | `/catalog`, `/catalog/{code}` |
| Installations | GET, POST | `/installations` |
| Dashboards | GET, POST | `/dashboards` |

`config_ref` on installations must be `vault://…` when provided.
