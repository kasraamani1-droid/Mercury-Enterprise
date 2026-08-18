# Aviation Network — Workflows

## Partnership lifecycle

1. Org A proposes partnership (type + permissions + optional expiry/contracts)
2. Status `proposed` → approve → `active`
3. Expired partnerships auto-block gated actions
4. Suspend/revoke statuses architecture-ready

## Collaboration (gated)

Active partnership with `collaboration` permission required:

- engineering_support / repair_quotation / technical_assistance
- share publications / work packages / digital records
- shared projects / document review / approval workflows

## Document share (gated)

Active partnership with `document_share` permission:

- Modes: read_only | download | approval_required
- Watermark default on; expiry optional; audit on create

## Messaging (gated for org scopes)

Active partnership with `messaging` for org_to_org / project / work_package / marketplace threads. User-to-user within tenant does not require a partnership.

## Directory

Entries created when profiles/events opt into visibility. Search is org-scoped in Program 14; partner-federated directory is future work.
