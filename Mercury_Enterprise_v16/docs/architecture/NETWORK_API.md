# Aviation Network API

Base: `/api/v1/network`  
Permissions: `network.read` | `network.manage`

| Area | Methods | Paths |
|------|---------|-------|
| Overview | GET | `/overview` |
| Directory | GET | `/directory/search` |
| Organizations | GET, POST | `/org-profiles` |
| Professionals | GET, POST | `/professionals` |
| Partnerships | GET, POST, POST | `/partnerships`, `/partnerships/{id}/approve` |
| Collaborations | GET, POST | `/collaborations` |
| Documents | GET, POST | `/document-shares` |
| Messaging | GET, POST, GET, POST | `/threads`, `/threads/{id}/messages`, `/messages` |
| Events | GET, POST | `/events` |

Cross-org create paths return **403** without an active partnership (and required permission).
