from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..org.service import OrganizationService
from .models import (
    DigitalStampProfile,
    PersonnelAuthorization,
    PersonnelEmployee,
    PersonnelQualification,
)
from .repository import PersonnelRepository
from .schemas import (
    AuthorizationCreate,
    AuthorizationOut,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
    QualificationCreate,
    QualificationOut,
    StampCreate,
    StampOut,
)

QUALIFICATION_TYPES = frozenset({"ame_license", "rating", "type_rating", "aca", "training", "other"})
AUTH_TYPES = frozenset({"aca", "independent_inspection", "stamp"})
EMPLOYEE_STATUSES = frozenset({"active", "inactive", "suspended"})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PersonnelService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PersonnelRepository(db)
        self.org = OrganizationService(db)

    def ensure_seed_data(self) -> None:
        org_id = "org-aviation-east"
        if self.org.repo.get_organization(org_id) is None:
            return

        now = _utcnow()
        pending = False

        employee = self.repo.get_employee("pers-op-east-001") or self.repo.get_by_org_number(org_id, "E-1001")
        if employee is None:
            employee = PersonnelEmployee(
                id="pers-op-east-001",
                organization_id=org_id,
                employee_number="E-1001",
                full_name="Demo AME Operator",
                department_id=None,
                position_title="Aircraft Maintenance Engineer",
                email="operator@aviation-east.example",
                status="active",
                user_username="operator",
                created_at=now,
                updated_at=now,
            )
            self.repo.add_employee(employee)
            self.repo.flush()
            pending = True

        if not any(q.id == "pers-qual-ame-001" for q in self.repo.list_qualifications(employee.id)):
            self.repo.add_qualification(
                PersonnelQualification(
                    id="pers-qual-ame-001",
                    employee_id=employee.id,
                    qualification_type="ame_license",
                    code="AME-M1",
                    description="Aircraft Maintenance Engineer — Category M1",
                    authority="Transport Canada",
                    issued_at=now,
                    expires_at=None,
                    status="active",
                    created_at=now,
                )
            )
            pending = True

        existing_auths = {a.id for a in self.repo.list_authorizations(employee.id)}
        # Least privilege: technician E-1001 must NOT hold ACA (segregation of duties).
        aca_tech = self.repo.get_authorization("pers-auth-aca-001")
        if aca_tech is not None and aca_tech.status == "active":
            aca_tech.status = "revoked"
            pending = True
        if "pers-auth-stamp-001" not in existing_auths:
            self.repo.add_authorization(
                PersonnelAuthorization(
                    id="pers-auth-stamp-001",
                    employee_id=employee.id,
                    auth_type="stamp",
                    scope="line_maintenance",
                    aircraft_model_id=None,
                    ata_chapter_id=None,
                    issued_at=now,
                    expires_at=None,
                    status="active",
                    created_at=now,
                )
            )
            pending = True

        if not any(s.id == "pers-stamp-001" for s in self.repo.list_stamps(employee.id)):
            self.repo.add_stamp(
                DigitalStampProfile(
                    id="pers-stamp-001",
                    employee_id=employee.id,
                    stamp_code="2468",
                    label="Demo AME PIN stamp",
                    status="active",
                    created_at=now,
                )
            )
            pending = True

        reviewer = self.repo.get_employee("pers-rev-east-001") or self.repo.get_by_org_number(org_id, "E-2001")
        if reviewer is None:
            reviewer = PersonnelEmployee(
                id="pers-rev-east-001",
                organization_id=org_id,
                employee_number="E-2001",
                full_name="Demo ACA Reviewer",
                department_id=None,
                position_title="Aircraft Certification Authority",
                email="reviewer@aviation-east.example",
                status="active",
                user_username="reviewer",
                created_at=now,
                updated_at=now,
            )
            self.repo.add_employee(reviewer)
            self.repo.flush()
            pending = True

        if not any(q.id == "pers-qual-ame-002" for q in self.repo.list_qualifications(reviewer.id)):
            self.repo.add_qualification(
                PersonnelQualification(
                    id="pers-qual-ame-002",
                    employee_id=reviewer.id,
                    qualification_type="ame_license",
                    code="AME-M2",
                    description="Aircraft Maintenance Engineer — Category M2",
                    authority="Transport Canada",
                    issued_at=now,
                    expires_at=None,
                    status="active",
                    created_at=now,
                )
            )
            pending = True

        rev_auths = {a.id for a in self.repo.list_authorizations(reviewer.id)}
        if "pers-auth-aca-002" not in rev_auths:
            self.repo.add_authorization(
                PersonnelAuthorization(
                    id="pers-auth-aca-002",
                    employee_id=reviewer.id,
                    auth_type="aca",
                    scope="line_maintenance",
                    aircraft_model_id="model-a320",
                    ata_chapter_id=None,
                    issued_at=now,
                    expires_at=None,
                    status="active",
                    created_at=now,
                )
            )
            pending = True
        if "pers-auth-ii-002" not in rev_auths:
            self.repo.add_authorization(
                PersonnelAuthorization(
                    id="pers-auth-ii-002",
                    employee_id=reviewer.id,
                    auth_type="independent_inspection",
                    scope="critical_tasks",
                    aircraft_model_id=None,
                    ata_chapter_id=None,
                    issued_at=now,
                    expires_at=None,
                    status="active",
                    created_at=now,
                )
            )
            pending = True

        # Third signer for segregation of duties (independent ≠ inspector ≠ performer).
        inspector = self.repo.get_employee("pers-ii-east-001") or self.repo.get_by_org_number(org_id, "E-3001")
        if inspector is None:
            inspector = PersonnelEmployee(
                id="pers-ii-east-001",
                organization_id=org_id,
                employee_number="E-3001",
                full_name="Demo Independent Inspector",
                department_id=None,
                position_title="Independent Inspector",
                email="inspector@aviation-east.example",
                status="active",
                user_username="admin",
                created_at=now,
                updated_at=now,
            )
            self.repo.add_employee(inspector)
            self.repo.flush()
            pending = True
        elif inspector.user_username != "admin":
            inspector.user_username = "admin"
            inspector.updated_at = now
            pending = True

        if not any(q.id == "pers-qual-ame-003" for q in self.repo.list_qualifications(inspector.id)):
            self.repo.add_qualification(
                PersonnelQualification(
                    id="pers-qual-ame-003",
                    employee_id=inspector.id,
                    qualification_type="ame_license",
                    code="AME-II",
                    description="Aircraft Maintenance Engineer — Independent Inspection",
                    authority="Transport Canada",
                    issued_at=now,
                    expires_at=None,
                    status="active",
                    created_at=now,
                )
            )
            pending = True

        ii_auths = {a.id for a in self.repo.list_authorizations(inspector.id)}
        if "pers-auth-ii-003" not in ii_auths:
            self.repo.add_authorization(
                PersonnelAuthorization(
                    id="pers-auth-ii-003",
                    employee_id=inspector.id,
                    auth_type="independent_inspection",
                    scope="critical_tasks",
                    aircraft_model_id=None,
                    ata_chapter_id=None,
                    issued_at=now,
                    expires_at=None,
                    status="active",
                    created_at=now,
                )
            )
            pending = True

        if pending:
            self.repo.commit()

    def _commit_or_conflict(self, *, detail: str) -> None:
        try:
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail=detail) from exc

    def resolve_org_id(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        requested_org_id: str | None,
    ) -> str:
        org_id = (requested_org_id or session_org_id).strip()
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=org_id)
        return org_id

    def assert_org_access(self, *, username: str, session_role: str, organization_id: str) -> None:
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=organization_id)

    def _get_org_employee(self, employee_id: str, *, username: str, session_role: str) -> PersonnelEmployee:
        row = self.repo.get_employee(employee_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Employee not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=row.organization_id)
        return row

    @staticmethod
    def employee_out(row: PersonnelEmployee) -> EmployeeOut:
        return EmployeeOut(
            id=row.id,
            organization_id=row.organization_id,
            employee_number=row.employee_number,
            full_name=row.full_name,
            department_id=row.department_id,
            position_title=row.position_title or "",
            email=row.email or "",
            status=row.status,
            user_username=row.user_username,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def qualification_out(row: PersonnelQualification) -> QualificationOut:
        return QualificationOut(
            id=row.id,
            employee_id=row.employee_id,
            qualification_type=row.qualification_type,
            code=row.code or "",
            description=row.description or "",
            authority=row.authority or "",
            issued_at=row.issued_at,
            expires_at=row.expires_at,
            status=row.status,
            created_at=row.created_at,
        )

    @staticmethod
    def authorization_out(row: PersonnelAuthorization) -> AuthorizationOut:
        return AuthorizationOut(
            id=row.id,
            employee_id=row.employee_id,
            auth_type=row.auth_type,
            scope=row.scope or "",
            aircraft_model_id=row.aircraft_model_id,
            ata_chapter_id=row.ata_chapter_id,
            issued_at=row.issued_at,
            expires_at=row.expires_at,
            status=row.status,
            created_at=row.created_at,
        )

    @staticmethod
    def stamp_out(row: DigitalStampProfile) -> StampOut:
        return StampOut(
            id=row.id,
            employee_id=row.employee_id,
            stamp_code=row.stamp_code,
            label=row.label or "",
            status=row.status,
            created_at=row.created_at,
        )

    def list_employees(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EmployeeOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        rows = self.repo.list_employees(
            organization_id=org_id,
            status=status,
            active_only=status is None,
            limit=limit,
            offset=offset,
        )
        return [self.employee_out(r) for r in rows]

    def create_employee(
        self,
        payload: EmployeeCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> EmployeeOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        status_value = (payload.status or "active").strip().lower()
        if status_value not in EMPLOYEE_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid employee status")
        number = payload.employee_number.strip()
        if self.repo.get_by_org_number(org_id, number):
            raise HTTPException(status_code=409, detail="Employee number already exists")
        now = _utcnow()
        row = PersonnelEmployee(
            organization_id=org_id,
            employee_number=number,
            full_name=payload.full_name.strip(),
            department_id=payload.department_id,
            position_title=(payload.position_title or "").strip(),
            email=(payload.email or "").strip(),
            status=status_value,
            user_username=(payload.user_username or None),
            created_at=now,
            updated_at=now,
        )
        self.repo.add_employee(row)
        self._commit_or_conflict(detail="Employee conflict")
        self.repo.refresh(row)
        return self.employee_out(row)

    def get_employee(self, employee_id: str, *, username: str, session_role: str) -> EmployeeOut:
        return self.employee_out(self._get_org_employee(employee_id, username=username, session_role=session_role))

    def update_employee(
        self,
        employee_id: str,
        payload: EmployeeUpdate,
        *,
        username: str,
        session_role: str,
    ) -> EmployeeOut:
        row = self._get_org_employee(employee_id, username=username, session_role=session_role)
        if payload.full_name is not None:
            row.full_name = payload.full_name.strip()
        if payload.department_id is not None:
            row.department_id = payload.department_id or None
        if payload.position_title is not None:
            row.position_title = payload.position_title.strip()
        if payload.email is not None:
            row.email = payload.email.strip()
        if payload.status is not None:
            status_value = payload.status.strip().lower()
            if status_value not in EMPLOYEE_STATUSES:
                raise HTTPException(status_code=400, detail="Invalid employee status")
            row.status = status_value
        if payload.user_username is not None:
            row.user_username = payload.user_username.strip() or None
        row.updated_at = _utcnow()
        self._commit_or_conflict(detail="Employee update conflict")
        self.repo.refresh(row)
        return self.employee_out(row)

    def list_qualifications(
        self, employee_id: str, *, username: str, session_role: str
    ) -> list[QualificationOut]:
        self._get_org_employee(employee_id, username=username, session_role=session_role)
        return [self.qualification_out(r) for r in self.repo.list_qualifications(employee_id)]

    def create_qualification(
        self,
        employee_id: str,
        payload: QualificationCreate,
        *,
        username: str,
        session_role: str,
    ) -> QualificationOut:
        employee = self._get_org_employee(employee_id, username=username, session_role=session_role)
        qtype = payload.qualification_type.strip().lower()
        if qtype not in QUALIFICATION_TYPES:
            raise HTTPException(status_code=400, detail="Invalid qualification type")
        row = PersonnelQualification(
            employee_id=employee.id,
            qualification_type=qtype,
            code=(payload.code or "").strip(),
            description=(payload.description or "").strip(),
            authority=(payload.authority or "").strip(),
            issued_at=payload.issued_at,
            expires_at=payload.expires_at,
            status=(payload.status or "active").strip().lower() or "active",
            created_at=_utcnow(),
        )
        self.repo.add_qualification(row)
        self._commit_or_conflict(detail="Qualification conflict")
        self.repo.refresh(row)
        return self.qualification_out(row)

    def list_authorizations(
        self, employee_id: str, *, username: str, session_role: str
    ) -> list[AuthorizationOut]:
        self._get_org_employee(employee_id, username=username, session_role=session_role)
        return [self.authorization_out(r) for r in self.repo.list_authorizations(employee_id)]

    def create_authorization(
        self,
        employee_id: str,
        payload: AuthorizationCreate,
        *,
        username: str,
        session_role: str,
    ) -> AuthorizationOut:
        employee = self._get_org_employee(employee_id, username=username, session_role=session_role)
        atype = payload.auth_type.strip().lower()
        if atype not in AUTH_TYPES:
            raise HTTPException(status_code=400, detail="Invalid authorization type")
        row = PersonnelAuthorization(
            employee_id=employee.id,
            auth_type=atype,
            scope=(payload.scope or "").strip(),
            aircraft_model_id=payload.aircraft_model_id,
            ata_chapter_id=payload.ata_chapter_id,
            issued_at=payload.issued_at,
            expires_at=payload.expires_at,
            status=(payload.status or "active").strip().lower() or "active",
            created_at=_utcnow(),
        )
        self.repo.add_authorization(row)
        self._commit_or_conflict(detail="Authorization conflict")
        self.repo.refresh(row)
        return self.authorization_out(row)

    def create_stamp(
        self,
        employee_id: str,
        payload: StampCreate,
        *,
        username: str,
        session_role: str,
    ) -> StampOut:
        employee = self._get_org_employee(employee_id, username=username, session_role=session_role)
        row = DigitalStampProfile(
            employee_id=employee.id,
            stamp_code=payload.stamp_code.strip(),
            label=(payload.label or "").strip(),
            status=(payload.status or "active").strip().lower() or "active",
            created_at=_utcnow(),
        )
        self.repo.add_stamp(row)
        self._commit_or_conflict(detail="Stamp conflict")
        self.repo.refresh(row)
        return self.stamp_out(row)

    def list_stamps(self, employee_id: str, *, username: str, session_role: str) -> list[StampOut]:
        employee = self._get_org_employee(employee_id, username=username, session_role=session_role)
        return [self.stamp_out(row) for row in self.repo.list_stamps(employee.id)]
