# Airworthiness Directives

Authorities: FAA · EASA · Transport Canada · Manufacturer · Other

Fields: number, revision, applicability, mandatory, compliance status, due date, publications, linked work orders, history.

`GET/POST /api/v1/planning/ads`  
`GET /api/v1/planning/ads/{id}`

Operator UI: Planning Ops desk and Engineering workspace open AD objects. Applicability is a text field (not an aircraft foreign key).

Revisions are unique per org (`ad_number` + `revision`). Soft-delete via `deleted_at`.
