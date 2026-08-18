# Data Dictionary — Universal Data Fabric

| Table | Purpose | Soft delete | Tenant |
|-------|---------|-------------|--------|
| `fabric_entity_types` | Canonical entity vocabulary | status | global |
| `fabric_passports` | Digital Passport / universal entity | `deleted_at` | `organization_id` |
| `fabric_passport_history` | Immutable revision snapshots | append-only | `organization_id` |
| `fabric_relationships` | Graph edges | `deleted_at` | `organization_id` |
| `fabric_events` | Enterprise timeline events | append-only | `organization_id` |
| `fabric_tags` | Tags / categories | unique per passport+tag | `organization_id` |
| `fabric_attachment_refs` | Links to `platform_file_objects` | `deleted_at` | `organization_id` |
| `fabric_retention_policies` | Retention / immutability rules | status | org or `*` |
| `fabric_legal_holds` | Legal hold | status active/released | `organization_id` |

## Entity type codes (catalog excerpt)

See `backend/app/fabric/catalog.py` for the full list (aircraft, component, work_order, job_card, AD/SB/EO, tool, marketplace_listing, authority_audit, …).

## Relationship types

`configured_as`, `installed_on`, `removed_from`, `performed_on`, `assigned_to`, `inspected_by`, `finding_of`, `supersedes`, `references`, `related_to`, `owned_by`, `part_of`, `derived_from`, `approves`, `releases`

## Event types

`created`, `updated`, `installed`, `removed`, `released`, `signed`, `approved`, `rejected`, `transferred`, `calibrated`, `inspected`, `published`, `archived`, `cancelled`, `deleted`
