# Personnel Management

Enterprise personnel records for aviation maintenance organizations.

## Domain

- **Employee** — org-scoped identity (employee number, department, position, linked username)
- **Qualifications** — AME license, ratings, type ratings, ACA, training (with expiry)
- **Authorizations** — ACA, independent inspection, stamp scope (model/ATA optional)
- **Digital stamp profiles** — rotatable stamp codes (prior stamps retired, not deleted)

## APIs

Base: `/api/v1/personnel`

| Method | Path |
|--------|------|
| GET/POST | `/employees` |
| GET/PATCH | `/employees/{id}` |
| GET/POST | `/employees/{id}/qualifications` |
| GET/POST | `/employees/{id}/authorizations` |
| GET/POST | `/employees/{id}/stamps` |

`GET .../stamps` lists profiles for the Personnel desk and employee object. `POST .../stamps` inserts a new profile; **prior stamps are not auto-retired**.

| Permission | Roles |
|------------|-------|
| `personnel.read` | Viewer+ |
| `personnel.manage` | Operator+ |

## Operator UI (Sprint 8e)

Personnel area (`#personnelWorkspace`) lists employees, qualification expiry alerts (display only: expired / expiring within 30 days), and stamp codes. Workspace Engine `employee` objects create qualifications/authorizations/stamps for Operator+. Job-card **Personnel context** chips open employees; inspect/release stay on job-card certification APIs.

## Audit

`personnel.employee.create`, `personnel.qualification.create`, `personnel.authorization.create`, `personnel.stamp.create`

## Related

[MAINTENANCE_CERTIFICATION.md](MAINTENANCE_CERTIFICATION.md) · [DIGITAL_SIGNATURES.md](DIGITAL_SIGNATURES.md) · [RBAC.md](RBAC.md)
