from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..shared import clamp_page
from .models import (
    DigitalStampProfile,
    PersonnelAuthorization,
    PersonnelEmployee,
    PersonnelQualification,
)


class PersonnelRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- employees ---
    def list_employees(
        self,
        *,
        organization_id: str,
        status: str | None = None,
        active_only: bool = True,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[PersonnelEmployee]:
        lim, off = clamp_page(limit, offset)
        stmt = (
            select(PersonnelEmployee)
            .where(PersonnelEmployee.organization_id == organization_id)
            .order_by(PersonnelEmployee.employee_number)
        )
        if status:
            stmt = stmt.where(PersonnelEmployee.status == status)
        elif active_only:
            stmt = stmt.where(PersonnelEmployee.status == "active")
        return list(self.db.scalars(stmt.limit(lim).offset(off)).all())

    def get_employee(self, employee_id: str, *, for_update: bool = False) -> PersonnelEmployee | None:
        stmt = select(PersonnelEmployee).where(PersonnelEmployee.id == employee_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_by_org_number(self, organization_id: str, employee_number: str) -> PersonnelEmployee | None:
        return self.db.scalar(
            select(PersonnelEmployee).where(
                PersonnelEmployee.organization_id == organization_id,
                PersonnelEmployee.employee_number == employee_number.strip(),
            )
        )

    def get_by_username(self, organization_id: str, username: str) -> PersonnelEmployee | None:
        return self.db.scalar(
            select(PersonnelEmployee).where(
                PersonnelEmployee.organization_id == organization_id,
                PersonnelEmployee.user_username == username.strip(),
            )
        )

    def add_employee(self, row: PersonnelEmployee) -> PersonnelEmployee:
        self.db.add(row)
        return row

    # --- qualifications ---
    def list_qualifications(self, employee_id: str) -> list[PersonnelQualification]:
        stmt = (
            select(PersonnelQualification)
            .where(PersonnelQualification.employee_id == employee_id)
            .order_by(PersonnelQualification.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def add_qualification(self, row: PersonnelQualification) -> PersonnelQualification:
        self.db.add(row)
        return row

    # --- authorizations ---
    def list_authorizations(self, employee_id: str) -> list[PersonnelAuthorization]:
        stmt = (
            select(PersonnelAuthorization)
            .where(PersonnelAuthorization.employee_id == employee_id)
            .order_by(PersonnelAuthorization.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_authorization(self, authorization_id: str) -> PersonnelAuthorization | None:
        return self.db.get(PersonnelAuthorization, authorization_id)

    def add_authorization(self, row: PersonnelAuthorization) -> PersonnelAuthorization:
        self.db.add(row)
        return row

    # --- stamps ---
    def list_stamps(self, employee_id: str) -> list[DigitalStampProfile]:
        stmt = (
            select(DigitalStampProfile)
            .where(DigitalStampProfile.employee_id == employee_id)
            .order_by(DigitalStampProfile.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def add_stamp(self, row: DigitalStampProfile) -> DigitalStampProfile:
        self.db.add(row)
        return row

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)

    def flush(self) -> None:
        self.db.flush()
