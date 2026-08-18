# Digital Twin API

Base: `/api/v1/twin`  
Permissions: `twin.read` | `twin.manage` (fabric/platform read/manage also accepted where noted)

| Area | Methods | Paths |
|------|---------|-------|
| Overview | GET | `/overview` |
| Search | GET | `/search` |
| Twins | GET, POST | `/twins` |
| Detail | GET | `/twins/{id}`, `/twins/by-uuid/{uuid}` |
| Passport | GET | `/twins/{id}/passport` |
| Lifecycle | POST | `/twins/{id}/lifecycle` |
| History | GET, POST | `/twins/{id}/history` |
| Configuration | GET, POST | `/twins/{id}/configurations` |
| Reliability | GET, POST | `/twins/{id}/reliability` |
| Relationships | GET | `/twins/{id}/relationships` |

Passport / thread deep-links remain on `/api/v1/fabric/*`.
