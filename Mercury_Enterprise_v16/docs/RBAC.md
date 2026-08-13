# Enterprise RBAC

## Session roles (runtime)

Administrator · Operator · Reviewer · Viewer — granted via `PERMISSIONS_BY_ROLE` in `backend/app/security/authorization.py`.

Administrator receives `*` (includes `publication.admin`, certification release, archive, etc.).

## Aviation personas (mapping layer)

Session roles remain Administrator / Operator / Reviewer / Viewer. Aviation personas (`PERSONA_PERMISSIONS`) document intended grants; **certify authority is enforced via personnel qualifications/authorizations + linked employee + live credentials**, not by persona name alone.

Personas guide documentation and future override engines:

| Persona | Typical access |
|---------|----------------|
| Technician | AMM/CMM/FIM/SDS/SSM/WM, tasks, sign performed work |
| Store | IPC, component read, store |
| Planner | MPD, planner, fleet, tasks read |
| Inspector | inspection approve, certification.sign, audit read |
| ACA | certification.release, logbook, signatures |
| Engineering | SRM/EO, configuration, engineering.read |
| Reliability / QA | compliance, audit, findings (qa.read) |
| Administrator | full |

## Domains covered

Org · Fleet · Components/Configuration · Publications · Personnel · Maintenance · Certification · Logbook · Signatures · Store/Planner/Inspector/Engineering/QA permissions

## Isolation

Organization membership gates all tenant data. Fleet → aircraft → ATA → task chain is enforced by org ownership checks on each resource.

## Future (Sprint 8+)

Individual permission overrides, ATA-scoped grants, fleet-scoped grants, and department/team/position binding beyond membership roles.
