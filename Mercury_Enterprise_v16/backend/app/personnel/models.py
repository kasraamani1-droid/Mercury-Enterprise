from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..models import uid


class PersonnelEmployee(Base):
    """Organization-scoped employee / technician record."""

    __tablename__ = "personnel_employees"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    employee_number: Mapped[str] = mapped_column(String(80), index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    position_title: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    user_username: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    qualifications: Mapped[list["PersonnelQualification"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    authorizations: Mapped[list["PersonnelAuthorization"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    stamps: Mapped[list["DigitalStampProfile"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "employee_number", name="uq_personnel_org_employee_number"),
        Index("ix_personnel_employees_org_status", "organization_id", "status"),
        Index("ix_personnel_employees_org_username", "organization_id", "user_username"),
    )


class PersonnelQualification(Base):
    """License, rating, type rating, ACA, or training qualification."""

    __tablename__ = "personnel_qualifications"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    employee_id: Mapped[str] = mapped_column(ForeignKey("personnel_employees.id"), index=True)
    # ame_license | rating | type_rating | aca | training | other
    qualification_type: Mapped[str] = mapped_column(String(40), index=True)
    code: Mapped[str] = mapped_column(String(80), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    authority: Mapped[str] = mapped_column(String(120), default="")
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee: Mapped[PersonnelEmployee] = relationship(back_populates="qualifications")

    __table_args__ = (Index("ix_personnel_qualifications_employee_type", "employee_id", "qualification_type"),)


class PersonnelAuthorization(Base):
    """Operational authorization (ACA, independent inspection, stamp)."""

    __tablename__ = "personnel_authorizations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    employee_id: Mapped[str] = mapped_column(ForeignKey("personnel_employees.id"), index=True)
    # aca | independent_inspection | stamp
    auth_type: Mapped[str] = mapped_column(String(40), index=True)
    scope: Mapped[str] = mapped_column(String(200), default="")
    aircraft_model_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee: Mapped[PersonnelEmployee] = relationship(back_populates="authorizations")

    __table_args__ = (Index("ix_personnel_authorizations_employee_type", "employee_id", "auth_type"),)


class DigitalStampProfile(Base):
    """Immutable digital stamp identity — rotate by inserting a new row."""

    __tablename__ = "digital_stamp_profiles"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    employee_id: Mapped[str] = mapped_column(ForeignKey("personnel_employees.id"), index=True)
    stamp_code: Mapped[str] = mapped_column(String(80), index=True)
    label: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee: Mapped[PersonnelEmployee] = relationship(back_populates="stamps")

    __table_args__ = (Index("ix_digital_stamp_profiles_employee_status", "employee_id", "status"),)
