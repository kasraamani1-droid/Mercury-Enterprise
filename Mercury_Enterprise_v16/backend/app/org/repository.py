from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..shared import clamp_page
from .models import Company, Department, Membership, OrgSite, OrgUser, Organization, Team


class OrgRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _apply_page(self, stmt, *, limit: int | None, offset: int | None):
        """Apply SQL pagination only when the caller opts in (API paths)."""
        if limit is None and (offset is None or offset == 0):
            return stmt
        lim, off = clamp_page(limit, offset)
        return stmt.limit(lim).offset(off)

    # Companies
    def list_companies(self, *, limit: int | None = None, offset: int | None = None) -> list[Company]:
        stmt = self._apply_page(select(Company).order_by(Company.name), limit=limit, offset=offset)
        return list(self.db.scalars(stmt).all())

    def get_company(self, company_id: str) -> Company | None:
        return self.db.get(Company, company_id)

    def get_company_by_code(self, code: str) -> Company | None:
        return self.db.scalar(select(Company).where(Company.code == code.upper()))

    def add_company(self, company: Company) -> Company:
        self.db.add(company)
        return company

    # Organizations
    def list_organizations(
        self,
        *,
        company_id: str | None = None,
        active_only: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Organization]:
        stmt = select(Organization).order_by(Organization.name)
        if company_id:
            stmt = stmt.where(Organization.company_id == company_id)
        if active_only:
            stmt = stmt.where(Organization.status == "active")
        stmt = self._apply_page(stmt, limit=limit, offset=offset)
        return list(self.db.scalars(stmt).all())

    def get_organization(self, organization_id: str) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def add_organization(self, organization: Organization) -> Organization:
        self.db.add(organization)
        return organization

    # Sites
    def list_sites(
        self,
        *,
        organization_id: str | None = None,
        active_only: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[OrgSite]:
        stmt = select(OrgSite).order_by(OrgSite.name)
        if organization_id:
            stmt = stmt.where(OrgSite.organization_id == organization_id)
        if active_only:
            stmt = stmt.where(OrgSite.status == "active")
        stmt = self._apply_page(stmt, limit=limit, offset=offset)
        return list(self.db.scalars(stmt).all())

    def get_site(self, site_id: str) -> OrgSite | None:
        return self.db.get(OrgSite, site_id)

    def add_site(self, site: OrgSite) -> OrgSite:
        self.db.add(site)
        return site

    # Departments
    def list_departments(
        self,
        *,
        organization_id: str,
        active_only: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Department]:
        stmt = select(Department).where(Department.organization_id == organization_id).order_by(Department.name)
        if active_only:
            stmt = stmt.where(Department.status == "active")
        stmt = self._apply_page(stmt, limit=limit, offset=offset)
        return list(self.db.scalars(stmt).all())

    def get_department(self, department_id: str) -> Department | None:
        return self.db.get(Department, department_id)

    def add_department(self, department: Department) -> Department:
        self.db.add(department)
        return department

    # Teams
    def list_teams(
        self,
        *,
        organization_id: str,
        department_id: str | None = None,
        active_only: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Team]:
        stmt = select(Team).where(Team.organization_id == organization_id).order_by(Team.name)
        if department_id:
            stmt = stmt.where(Team.department_id == department_id)
        if active_only:
            stmt = stmt.where(Team.status == "active")
        stmt = self._apply_page(stmt, limit=limit, offset=offset)
        return list(self.db.scalars(stmt).all())

    def get_team(self, team_id: str) -> Team | None:
        return self.db.get(Team, team_id)

    def add_team(self, team: Team) -> Team:
        self.db.add(team)
        return team

    # Users / memberships
    def get_user_by_username(self, username: str) -> OrgUser | None:
        return self.db.scalar(select(OrgUser).where(OrgUser.username == username))

    def list_users(self, *, limit: int | None = None, offset: int | None = None) -> list[OrgUser]:
        stmt = self._apply_page(select(OrgUser).order_by(OrgUser.username), limit=limit, offset=offset)
        return list(self.db.scalars(stmt).all())

    def add_user(self, user: OrgUser) -> OrgUser:
        self.db.add(user)
        return user

    def list_memberships(
        self,
        *,
        organization_id: str | None = None,
        username: str | None = None,
        user_id: str | None = None,
        active_only: bool = False,
        with_user: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Membership]:
        stmt = select(Membership)
        if with_user:
            stmt = stmt.options(joinedload(Membership.user))
        if organization_id:
            stmt = stmt.where(Membership.organization_id == organization_id)
        if user_id:
            stmt = stmt.where(Membership.user_id == user_id)
        elif username:
            user = self.get_user_by_username(username)
            if user is None:
                return []
            stmt = stmt.where(Membership.user_id == user.id)
        if active_only:
            stmt = stmt.where(Membership.status == "active")
        stmt = self._apply_page(stmt.order_by(Membership.created_at.desc()), limit=limit, offset=offset)
        return list(self.db.scalars(stmt).unique().all())

    def find_membership_duplicate(
        self,
        *,
        user_id: str,
        organization_id: str,
        role: str,
        site_id: str | None,
        department_id: str | None,
        team_id: str | None,
    ) -> Membership | None:
        """Application-level duplicate check (NULL-safe; SQLite UNIQUE treats NULLs as distinct)."""
        stmt = select(Membership).where(
            Membership.user_id == user_id,
            Membership.organization_id == organization_id,
            Membership.role == role,
            Membership.status == "active",
        )
        rows = list(self.db.scalars(stmt).all())
        for row in rows:
            if (
                row.site_id == site_id
                and row.department_id == department_id
                and row.team_id == team_id
            ):
                return row
        return None

    def add_membership(self, membership: Membership) -> Membership:
        self.db.add(membership)
        return membership

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)

    def flush(self) -> None:
        self.db.flush()
