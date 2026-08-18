"""Program A: Mercury Enterprise Platform Foundation tables."""

from __future__ import annotations

from alembic import op

revision = "20260813_0012"
down_revision = "20260813_0011"
branch_labels = None
depends_on = None

PLATFORM_TABLES = {
    "platform_api_keys",
    "platform_pats",
    "platform_mfa_enrollments",
    "platform_business_units",
    "platform_cost_centers",
    "platform_facilities",
    "platform_role_templates",
    "platform_custom_roles",
    "platform_temporary_access",
    "platform_permission_audits",
    "platform_workflow_definitions",
    "platform_workflow_instances",
    "platform_workflow_transition_logs",
    "platform_notifications",
    "platform_file_objects",
    "platform_search_documents",
    "platform_settings",
    "platform_feature_flags",
    "platform_org_feature_flags",
}


def upgrade() -> None:
    from app.database import Base
    from app.platform import models as platform_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in PLATFORM_TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    for name in (
        "platform_org_feature_flags",
        "platform_feature_flags",
        "platform_settings",
        "platform_search_documents",
        "platform_file_objects",
        "platform_notifications",
        "platform_workflow_transition_logs",
        "platform_workflow_instances",
        "platform_workflow_definitions",
        "platform_permission_audits",
        "platform_temporary_access",
        "platform_custom_roles",
        "platform_role_templates",
        "platform_facilities",
        "platform_cost_centers",
        "platform_business_units",
        "platform_mfa_enrollments",
        "platform_pats",
        "platform_api_keys",
    ):
        op.drop_table(name)
