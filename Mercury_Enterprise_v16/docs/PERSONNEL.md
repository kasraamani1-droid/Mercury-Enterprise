# Personnel Management

Enterprise personnel records for aviation maintenance organizations.

## Domain

- **Employee** — org-scoped identity (employee number, department, position, linked username)
- **Qualifications** — AME license, ratings, type ratings, ACA, training (with expiry)
- **Authorizations** — ACA, independent inspection, stamp scope (model/ATA optional)
- **Digital stamp profiles** — rotatable stamp codes (prior stamps retired, not deleted)

## APIs

Base: `/api/v1/personnel`

| Permission | Roles |
|------------|-------|
| `personnel.read` | Viewer+ |
| `personnel.manage` | Operator+ |

## Audit

`personnel.employee.create`, `personnel.qualification.create`, `personnel.authorization.create`, `personnel.stamp.create`

## Related

[MAINTENANCE_CERTIFICATION.md](MAINTENANCE_CERTIFICATION.md) · [DIGITAL_SIGNATURES.md](DIGITAL_SIGNATURES.md) · [RBAC.md](RBAC.md)
