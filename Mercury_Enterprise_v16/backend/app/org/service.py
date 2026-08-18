from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..security.authorization import Role, has_permissions, parse_role
from ..security.api_key import MACHINE_OPERATOR, configured_machine_org_id
from ..security.operators import (
    hash_password,
    operator_store,
    password_needs_rehash,
    validate_operator_name,
    validate_password,
    verify_password,
)
from .models import Company, Department, Membership, OrgSite, OrgUser, Organization, Team
from .repository import OrgRepository
from .schemas import (
    CompanyCreate,
    CompanyOut,
    DepartmentCreate,
    DepartmentOut,
    MembershipCreate,
    MembershipOut,
    OrganizationCreate,
    OrganizationOut,
    SiteCreate,
    SiteOut,
    TeamCreate,
    TeamOut,
    UserCreate,
    UserOut,
)

logger = logging.getLogger("mercury.org")

# Organization memberships must never grant platform-admin (* / admin.system).
_MEMBERSHIP_ROLES = frozenset(
    {
        Role.OPERATOR.value,
        Role.REVIEWER.value,
        Role.VIEWER.value,
    }
)
_ROLE_RANK = {
    Role.OPERATOR.value: 3,
    Role.REVIEWER.value: 2,
    Role.VIEWER.value: 1,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OrganizationService:
    def __init__(self, db: Session) -> None:
        self.repo = OrgRepository(db)

    def ensure_seed_data(
        self,
        *,
        default_password_hash: str,
        operator_roles: dict[str, str],
        auth_password: str = "",
    ) -> None:
        """Idempotent seed matching legacy aviation orgs/sites."""
        if self.repo.list_companies():
            self._ensure_users_and_memberships(default_password_hash, operator_roles, auth_password=auth_password)
            return

        company = Company(
            id="company-mercury",
            name="Mercury Aviation Group",
            code="MAG",
            status="active",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_company(company)

        east = Organization(
            id="org-aviation-east",
            company_id=company.id,
            name="Mercury Aviation East",
            code="EAST",
            status="active",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        west = Organization(
            id="org-aviation-west",
            company_id=company.id,
            name="Mercury Aviation West",
            code="WEST",
            status="active",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_organization(east)
        self.repo.add_organization(west)

        for site in (
            OrgSite(
                id="site-cyul",
                organization_id=east.id,
                name="CYUL Montréal",
                code="CYUL",
                timezone="America/Toronto",
                created_at=_utcnow(),
                updated_at=_utcnow(),
            ),
            OrgSite(
                id="site-cyyz",
                organization_id=east.id,
                name="CYYZ Toronto",
                code="CYYZ",
                timezone="America/Toronto",
                created_at=_utcnow(),
                updated_at=_utcnow(),
            ),
            OrgSite(
                id="site-cyvr",
                organization_id=west.id,
                name="CYVR Vancouver",
                code="CYVR",
                timezone="America/Vancouver",
                created_at=_utcnow(),
                updated_at=_utcnow(),
            ),
        ):
            self.repo.add_site(site)

        ops_east = Department(
            id="dept-ops-east",
            organization_id=east.id,
            site_id="site-cyul",
            name="Operations East",
            code="OPS",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_department(ops_east)
        self.repo.add_team(
            Team(
                id="team-watch-east",
                organization_id=east.id,
                department_id=ops_east.id,
                name="Watch Floor East",
                code="WATCH",
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
        )
        self.repo.commit()
        self._ensure_users_and_memberships(default_password_hash, operator_roles, auth_password=auth_password)

    def _ensure_users_and_memberships(
        self,
        default_password_hash: str,
        operator_roles: dict[str, str],
        *,
        auth_password: str = "",
    ) -> None:
        orgs = self.repo.list_organizations(active_only=True)
        if not orgs:
            return
        # Prefer stable seeded east org as default for non-admins.
        default_org = next((o for o in orgs if o.id == "org-aviation-east"), orgs[0])
        sites_by_org = {org.id: self.repo.list_sites(organization_id=org.id, active_only=True) for org in orgs}
        default_site_id = sites_by_org.get(default_org.id, [None])[0].id if sites_by_org.get(default_org.id) else None

        pending = False
        for username, role in operator_roles.items():
            user = self.repo.get_user_by_username(username)
            if user is None:
                user = OrgUser(
                    username=username,
                    display_name=username.title(),
                    password_hash=default_password_hash,
                    platform_role=role,
                    status="active",
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
                self.repo.add_user(user)
                self.repo.flush()
                pending = True
            elif not (user.platform_role or "").strip():
                user.platform_role = role
                user.updated_at = _utcnow()
                pending = True
            if (
                user is not None
                and auth_password
                and password_needs_rehash(user.password_hash)
                and verify_password(auth_password, user.password_hash)
            ):
                user.password_hash = default_password_hash
                user.updated_at = _utcnow()
                pending = True

            # Platform administrators are not modeled via membership elevation; seed
            # memberships use Operator/Reviewer/Viewer except we still record admin
            # presence as Viewer-scoped access markers for org listing convenience.
            # Actual platform admin is determined solely from operator_store.
            membership_role = role if role in _MEMBERSHIP_ROLES else Role.VIEWER.value
            if role == Role.ADMINISTRATOR.value:
                targets = orgs
                membership_role = Role.OPERATOR.value  # org-scoped ceiling
            else:
                targets = [default_org]

            existing = self.repo.list_memberships(username=username, active_only=True)
            existing_orgs = {m.organization_id for m in existing}
            for org in targets:
                if org.id in existing_orgs:
                    continue
                org_sites = sites_by_org.get(org.id) or []
                site_id = org_sites[0].id if org_sites else default_site_id
                self.repo.add_membership(
                    Membership(
                        user_id=user.id,
                        organization_id=org.id,
                        site_id=site_id,
                        role=membership_role,
                        status="active",
                        created_at=_utcnow(),
                        updated_at=_utcnow(),
                    )
                )
                pending = True
        if pending:
            self.repo.commit()

    # --- serialization helpers ---
    @staticmethod
    def company_out(row: Company) -> CompanyOut:
        return CompanyOut(id=row.id, name=row.name, code=row.code, status=row.status, created_at=row.created_at)

    @staticmethod
    def organization_out(row: Organization) -> OrganizationOut:
        return OrganizationOut(
            organization_id=row.id,
            company_id=row.company_id,
            name=row.name,
            code=row.code,
            status=row.status,
        )

    @staticmethod
    def site_out(row: OrgSite) -> SiteOut:
        return SiteOut(
            site_id=row.id,
            organization_id=row.organization_id,
            name=row.name,
            code=row.code,
            status=row.status,
            timezone=row.timezone,
        )

    @staticmethod
    def department_out(row: Department) -> DepartmentOut:
        return DepartmentOut(
            id=row.id,
            organization_id=row.organization_id,
            site_id=row.site_id,
            name=row.name,
            code=row.code,
            status=row.status,
        )

    @staticmethod
    def team_out(row: Team) -> TeamOut:
        return TeamOut(
            id=row.id,
            organization_id=row.organization_id,
            department_id=row.department_id,
            name=row.name,
            code=row.code,
            status=row.status,
        )

    @staticmethod
    def user_out(row: OrgUser) -> UserOut:
        return UserOut(
            id=row.id,
            username=row.username,
            display_name=row.display_name,
            email=row.email,
            status=row.status,
        )

    @staticmethod
    def membership_out(row: Membership, username: str) -> MembershipOut:
        return MembershipOut(
            id=row.id,
            username=username,
            organization_id=row.organization_id,
            role=row.role,
            site_id=row.site_id,
            department_id=row.department_id,
            team_id=row.team_id,
            status=row.status,
        )

    # --- access control ---
    def global_role_for(self, username: str, session_role: str = "") -> str:
        """Platform privilege must come from the login directory, never session elevation."""
        record = operator_store.get(username)
        if record:
            return record["role"]
        return session_role

    def is_platform_admin(self, username: str, session_role: str = "") -> bool:
        return has_permissions(self.global_role_for(username, session_role), ("admin.system",))

    def user_memberships(self, username: str) -> list[Membership]:
        return self.repo.list_memberships(username=username, active_only=True)

    def allowed_organization_ids(self, username: str, session_role: str = "") -> set[str] | None:
        """None means all organizations (platform admin)."""
        if self.is_platform_admin(username, session_role):
            return None
        # Machine API-key principal: synthetic single-org membership (no DB row).
        if username == MACHINE_OPERATOR:
            org_id = configured_machine_org_id()
            return {org_id} if org_id else set()
        return {m.organization_id for m in self.user_memberships(username)}

    def assert_org_access(self, *, username: str, session_role: str, organization_id: str) -> None:
        org = self.repo.get_organization(organization_id)
        if org is None or org.status != "active":
            raise HTTPException(status_code=404, detail="Organization not found")
        allowed = self.allowed_organization_ids(username, session_role)
        if allowed is None:
            return
        if organization_id not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")

    def assert_site_in_org(self, *, organization_id: str, site_id: str) -> OrgSite:
        site = self.repo.get_site(site_id)
        if site is None or site.organization_id != organization_id or site.status != "active":
            raise HTTPException(status_code=404, detail="Site not found")
        return site

    def default_context_for_user(self, username: str, login_role: str) -> tuple[str, str]:
        if self.is_platform_admin(username, login_role):
            orgs = self.repo.list_organizations(active_only=True)
            if not orgs:
                raise HTTPException(status_code=500, detail="No organizations configured")
            preferred = next((o for o in orgs if o.id == "org-aviation-east"), orgs[0])
            sites = self.repo.list_sites(organization_id=preferred.id, active_only=True)
            if not sites:
                raise HTTPException(status_code=500, detail="Organization has no sites")
            return preferred.id, sites[0].id

        memberships = self.user_memberships(username)
        if not memberships:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No organization membership",
            )
        m = memberships[0]
        site_id = m.site_id
        if site_id:
            site = self.repo.get_site(site_id)
            if site is None or site.organization_id != m.organization_id or site.status != "active":
                site_id = None
        if not site_id:
            sites = self.repo.list_sites(organization_id=m.organization_id, active_only=True)
            if not sites:
                raise HTTPException(status_code=500, detail="Organization has no sites")
            site_id = sites[0].id
        return m.organization_id, site_id

    def organizations_for_session(self, username: str, session_role: str) -> list[OrganizationOut]:
        rows = self.repo.list_organizations(active_only=True)
        allowed = self.allowed_organization_ids(username, session_role)
        if allowed is not None:
            rows = [r for r in rows if r.id in allowed]
        return [self.organization_out(r) for r in rows]

    def sites_for_session(
        self,
        username: str,
        session_role: str,
        organization_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[SiteOut]:
        self.assert_org_access(username=username, session_role=session_role, organization_id=organization_id)
        return [
            self.site_out(s)
            for s in self.repo.list_sites(
                organization_id=organization_id, active_only=True, limit=limit, offset=offset
            )
        ]

    def get_organization_out(self, organization_id: str) -> OrganizationOut:
        row = self.repo.get_organization(organization_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        return self.organization_out(row)

    def get_site_out(self, organization_id: str, site_id: str) -> SiteOut:
        site = self.assert_site_in_org(organization_id=organization_id, site_id=site_id)
        return self.site_out(site)

    def _commit_or_conflict(self, *, conflict_detail: str) -> None:
        try:
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail=conflict_detail) from exc

    # --- mutations ---
    def create_company(self, payload: CompanyCreate) -> CompanyOut:
        code = payload.code.strip().upper()
        if self.repo.get_company_by_code(code):
            raise HTTPException(status_code=409, detail="Company code already exists")
        row = Company(
            name=payload.name.strip(),
            code=code,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_company(row)
        self._commit_or_conflict(conflict_detail="Company already exists")
        self.repo.refresh(row)
        return self.company_out(row)

    def create_organization(self, payload: OrganizationCreate) -> OrganizationOut:
        if self.repo.get_company(payload.company_id) is None:
            raise HTTPException(status_code=404, detail="Company not found")
        org_id = payload.organization_id.strip()
        if self.repo.get_organization(org_id):
            raise HTTPException(status_code=409, detail="Organization already exists")
        row = Organization(
            id=org_id,
            company_id=payload.company_id,
            name=payload.name.strip(),
            code=payload.code.strip().upper(),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_organization(row)
        self._commit_or_conflict(conflict_detail="Organization already exists")
        self.repo.refresh(row)
        return self.organization_out(row)

    def create_site(self, payload: SiteCreate) -> SiteOut:
        if self.repo.get_organization(payload.organization_id) is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        site_id = payload.site_id.strip()
        if self.repo.get_site(site_id):
            raise HTTPException(status_code=409, detail="Site already exists")
        row = OrgSite(
            id=site_id,
            organization_id=payload.organization_id,
            name=payload.name.strip(),
            code=payload.code.strip().upper(),
            timezone=payload.timezone or "UTC",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_site(row)
        self._commit_or_conflict(conflict_detail="Site code already exists in organization")
        self.repo.refresh(row)
        return self.site_out(row)

    def create_department(self, payload: DepartmentCreate) -> DepartmentOut:
        if self.repo.get_organization(payload.organization_id) is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        if payload.site_id:
            self.assert_site_in_org(organization_id=payload.organization_id, site_id=payload.site_id)
        row = Department(
            organization_id=payload.organization_id,
            site_id=payload.site_id,
            name=payload.name.strip(),
            code=payload.code.strip().upper(),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_department(row)
        self._commit_or_conflict(conflict_detail="Department code already exists in organization")
        self.repo.refresh(row)
        return self.department_out(row)

    def create_team(self, payload: TeamCreate) -> TeamOut:
        dept = self.repo.get_department(payload.department_id)
        if dept is None or dept.organization_id != payload.organization_id:
            raise HTTPException(status_code=404, detail="Department not found")
        row = Team(
            organization_id=payload.organization_id,
            department_id=payload.department_id,
            name=payload.name.strip(),
            code=payload.code.strip().upper(),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_team(row)
        self._commit_or_conflict(conflict_detail="Team code already exists in department")
        self.repo.refresh(row)
        return self.team_out(row)

    def create_user(self, payload: UserCreate) -> UserOut:
        try:
            username = validate_operator_name(payload.username)
            password = validate_password(payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if self.repo.get_user_by_username(username):
            raise HTTPException(status_code=409, detail="User already exists")
        row = OrgUser(
            username=username,
            display_name=(payload.display_name or username).strip(),
            email=(payload.email or "").strip(),
            password_hash=hash_password(password),
            platform_role=Role.VIEWER.value,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_user(row)
        self._commit_or_conflict(conflict_detail="User already exists")
        self.repo.refresh(row)
        return self.user_out(row)

    def create_membership(self, payload: MembershipCreate) -> MembershipOut:
        user = self.repo.get_user_by_username(payload.username)
        if user is None or user.status != "active":
            raise HTTPException(status_code=404, detail="User not found")
        if self.repo.get_organization(payload.organization_id) is None:
            raise HTTPException(status_code=404, detail="Organization not found")

        role = parse_role(payload.role).value
        if role not in _MEMBERSHIP_ROLES:
            raise HTTPException(
                status_code=400,
                detail="Membership role cannot be Administrator; use Operator, Reviewer, or Viewer",
            )

        if payload.site_id:
            self.assert_site_in_org(organization_id=payload.organization_id, site_id=payload.site_id)
        if payload.department_id:
            dept = self.repo.get_department(payload.department_id)
            if dept is None or dept.organization_id != payload.organization_id:
                raise HTTPException(status_code=404, detail="Department not found")
        if payload.team_id:
            team = self.repo.get_team(payload.team_id)
            if team is None or team.organization_id != payload.organization_id:
                raise HTTPException(status_code=404, detail="Team not found")
            if payload.department_id and team.department_id != payload.department_id:
                raise HTTPException(status_code=400, detail="Team does not belong to department")

        if self.repo.find_membership_duplicate(
            user_id=user.id,
            organization_id=payload.organization_id,
            role=role,
            site_id=payload.site_id,
            department_id=payload.department_id,
            team_id=payload.team_id,
        ):
            raise HTTPException(status_code=409, detail="Membership already exists")

        row = Membership(
            user_id=user.id,
            organization_id=payload.organization_id,
            site_id=payload.site_id,
            department_id=payload.department_id,
            team_id=payload.team_id,
            role=role,
            notes=payload.notes or "",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_membership(row)
        self._commit_or_conflict(conflict_detail="Membership already exists")
        self.repo.refresh(row)
        return self.membership_out(row, user.username)

    def effective_role_for_org(self, username: str, login_role: str, organization_id: str) -> str:
        """Org-scoped role for session; never elevates to platform Administrator."""
        if self.is_platform_admin(username, login_role):
            return self.global_role_for(username, login_role)

        memberships = [m for m in self.user_memberships(username) if m.organization_id == organization_id]
        if not memberships:
            return login_role if login_role in _MEMBERSHIP_ROLES else Role.VIEWER.value

        best = max(
            (m.role for m in memberships if m.role in _ROLE_RANK),
            key=lambda r: _ROLE_RANK[r],
            default=Role.VIEWER.value,
        )
        return best
