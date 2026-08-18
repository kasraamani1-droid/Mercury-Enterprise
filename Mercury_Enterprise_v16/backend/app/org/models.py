from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..models import uid


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organizations: Mapped[list["Organization"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)  # stable public organization_id
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Company] = relationship(back_populates="organizations")
    sites: Mapped[list["OrgSite"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    departments: Mapped[list["Department"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_org_company_code"),)


class OrgSite(Base):
    __tablename__ = "org_sites"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)  # stable public site_id
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped[Organization] = relationship(back_populates="sites")
    departments: Mapped[list["Department"]] = relationship(back_populates="site")

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_site_org_code"),)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("org_sites.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped[Organization] = relationship(back_populates="departments")
    site: Mapped[OrgSite | None] = relationship(back_populates="departments")
    teams: Mapped[list["Team"]] = relationship(back_populates="department", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_dept_org_code"),)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    department: Mapped[Department] = relationship(back_populates="teams")

    __table_args__ = (UniqueConstraint("department_id", "code", name="uq_team_dept_code"),)


class OrgUser(Base):
    """Directory identity (operator username). Passwords remain hashed."""

    __tablename__ = "org_users"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    platform_role: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Membership(Base):
    """Organization-scoped RBAC binding for a user."""

    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("org_users.id"), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("org_sites.id"), nullable=True, index=True)
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"), nullable=True, index=True)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(40), default="Viewer", index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")

    user: Mapped[OrgUser] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            "site_id",
            "department_id",
            "team_id",
            "role",
            name="uq_membership_scope",
        ),
        Index("ix_memberships_user_org", "user_id", "organization_id"),
        Index("ix_memberships_org_status", "organization_id", "status"),
    )
