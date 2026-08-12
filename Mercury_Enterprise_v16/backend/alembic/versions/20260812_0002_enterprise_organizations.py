"""Enterprise organizations hierarchy (companies → orgs → sites → departments → teams → users/memberships)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260812_0002"
down_revision = "20260810_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_companies_name", "companies", ["name"], unique=True)
    op.create_index("ix_companies_code", "companies", ["code"], unique=True)

    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("company_id", sa.String(length=80), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("company_id", "code", name="uq_org_company_code"),
    )
    op.create_index("ix_organizations_company_id", "organizations", ["company_id"])
    op.create_index("ix_organizations_name", "organizations", ["name"])
    op.create_index("ix_organizations_code", "organizations", ["code"])

    op.create_table(
        "org_sites",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_site_org_code"),
    )
    op.create_index("ix_org_sites_organization_id", "org_sites", ["organization_id"])

    op.create_table(
        "departments",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("site_id", sa.String(length=80), sa.ForeignKey("org_sites.id"), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_dept_org_code"),
    )
    op.create_index("ix_departments_organization_id", "departments", ["organization_id"])
    op.create_index("ix_departments_site_id", "departments", ["site_id"])

    op.create_table(
        "teams",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("department_id", sa.String(length=80), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("department_id", "code", name="uq_team_dept_code"),
    )
    op.create_index("ix_teams_organization_id", "teams", ["organization_id"])
    op.create_index("ix_teams_department_id", "teams", ["department_id"])

    op.create_table(
        "org_users",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_org_users_username", "org_users", ["username"], unique=True)

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("user_id", sa.String(length=80), sa.ForeignKey("org_users.id"), nullable=False),
        sa.Column("organization_id", sa.String(length=80), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("site_id", sa.String(length=80), sa.ForeignKey("org_sites.id"), nullable=True),
        sa.Column("department_id", sa.String(length=80), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("team_id", sa.String(length=80), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "organization_id",
            "site_id",
            "department_id",
            "team_id",
            "role",
            name="uq_membership_scope",
        ),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    op.create_index("ix_memberships_site_id", "memberships", ["site_id"])
    op.create_index("ix_memberships_department_id", "memberships", ["department_id"])
    op.create_index("ix_memberships_team_id", "memberships", ["team_id"])
    op.create_index("ix_memberships_role", "memberships", ["role"])
    op.create_index("ix_memberships_status", "memberships", ["status"])
    op.create_index("ix_memberships_user_org", "memberships", ["user_id", "organization_id"])
    op.create_index("ix_memberships_org_status", "memberships", ["organization_id", "status"])
    op.create_index("ix_companies_status", "companies", ["status"])
    op.create_index("ix_organizations_status", "organizations", ["status"])
    op.create_index("ix_org_sites_status", "org_sites", ["status"])
    op.create_index("ix_departments_status", "departments", ["status"])
    op.create_index("ix_teams_status", "teams", ["status"])
    op.create_index("ix_org_users_status", "org_users", ["status"])


def downgrade() -> None:
    op.drop_table("memberships")
    op.drop_table("org_users")
    op.drop_table("teams")
    op.drop_table("departments")
    op.drop_table("org_sites")
    op.drop_table("organizations")
    op.drop_table("companies")
