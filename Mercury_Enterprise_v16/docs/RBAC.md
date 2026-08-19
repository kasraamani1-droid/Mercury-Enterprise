# Enterprise RBAC

## Session roles (runtime)

Administrator · Operator · Reviewer · Viewer — granted via `PERMISSIONS_BY_ROLE` in `backend/app/security/authorization.py`.

Administrator receives `*` (includes `publication.admin`, certification release, archive, etc.).

## Aviation personas (mapping layer)

Session roles remain Administrator / Operator / Reviewer / Viewer. Aviation personas (`PERSONA_PERMISSIONS`) document intended grants; **certify authority is enforced via personnel qualifications/authorizations + linked employee + live credentials**, not by persona name alone.

Personas guide documentation and future override engines:

| Persona | Typical access |
|---------|----------------|
| Technician | AMM/CMM/FIM/SDS/SSM/WM, tasks, job cards, `work_order.execute`, sign performed work |
| Store | IPC, component read, store, work order read |
| Planner | MPD, planner, fleet, work package/order manage |
| Supervisor | Assign/reassign job cards, monitor progress, work_order.manage |
| Inspector | inspection approve/reject/rework, certification.sign, audit read |
| ACA | certification.release, logbook, signatures, job card release |
| Engineering | SRM/EO, configuration, engineering.read, waiting-engineering unblock |
| Reliability / QA | compliance, audit, findings (qa.read), inspection queues |
| Manager | Dashboards & reports across work orders |
| Administrator | full |

## Domains covered

Org · Fleet · Components/Configuration · Publications · Personnel · Maintenance · Work Orders / Job Cards · Certification · Logbook · Signatures · Store/Planner/Inspector/Engineering/QA permissions · Logistics (session: Viewer/Reviewer read; Operator/Administrator stores & purchase; Reviewer tools)

Aviation persona names (Technician, Store, Planner, …) are **not** session principals. The Logistics operator UI hides stores mutations unless the session role is Operator or Administrator. The Planning operator UI hides generate/create mutations unless the session role is Operator or Administrator (`planning.manage`). The Technical Library UI hides create/draft-revision unless Operator/Administrator (`publication.manage`); archive, access classification, and later revision activation stay Administrator-only (`publication.admin`). The Personnel UI hides employee/qualification/stamp create unless Operator/Administrator (`personnel.manage`).

## Isolation

Organization membership gates all tenant data. Fleet → aircraft → ATA → work package → work order → job card → task chain is enforced by org ownership checks on each resource.

Incident Command writes (status / events / evidence) use `_get_scoped_incident` (404 on cross-tenant UUID). WebSocket incident events are org/site scoped. See [engineering/TENANT_ISOLATION.md](engineering/TENANT_ISOLATION.md).

Approval inbox (`/api/v1/approvals`) is org/site scoped: Operators may `approval.request`; Reviewers/Admins may `approval.review`. Rows persist in `approval_requests` (see [engineering/APPROVAL_PERSISTENCE.md](engineering/APPROVAL_PERSISTENCE.md)).

## Future

Individual permission overrides, ATA-scoped grants, fleet-scoped grants, and department/team/position binding beyond membership roles.
