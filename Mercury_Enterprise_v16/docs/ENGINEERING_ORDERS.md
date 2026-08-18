# Engineering Orders

Draft → review → `POST .../approve` → approved/released. Effectivity, work instructions, references, publications, linked work orders, history.

`GET/POST /api/v1/planning/engineering-orders`  
`GET /api/v1/planning/engineering-orders/{id}`  
`POST /api/v1/planning/engineering-orders/{id}/approve`

Approve from draft/in_review only (HTTP 409 otherwise). Operator UI: Planning desk create + EO object approve.
