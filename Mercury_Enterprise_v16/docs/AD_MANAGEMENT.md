# Airworthiness Directives

Authorities: FAA · EASA · Transport Canada · Manufacturer · Other

Fields: number, revision, applicability, mandatory, compliance status, due date, publications, linked work orders, history.

`GET/POST /api/v1/planning/ads`

Revisions are unique per org (`ad_number` + `revision`). Soft-delete via `deleted_at`.
