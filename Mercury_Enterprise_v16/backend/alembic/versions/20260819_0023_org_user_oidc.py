"""OIDC subject/issuer columns on org_users for production IAM mapping."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260819_0023"
down_revision = "20260814_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "org_users" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("org_users")}
    if "oidc_issuer" not in columns:
        op.add_column("org_users", sa.Column("oidc_issuer", sa.String(length=400), nullable=True))
    if "oidc_subject" not in columns:
        op.add_column("org_users", sa.Column("oidc_subject", sa.String(length=255), nullable=True))
    indexes = {idx["name"] for idx in inspector.get_indexes("org_users")}
    if "ix_org_users_oidc_issuer_subject" not in indexes:
        op.create_index("ix_org_users_oidc_issuer_subject", "org_users", ["oidc_issuer", "oidc_subject"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "org_users" not in inspector.get_table_names():
        return
    indexes = {idx["name"] for idx in inspector.get_indexes("org_users")}
    if "ix_org_users_oidc_issuer_subject" in indexes:
        op.drop_index("ix_org_users_oidc_issuer_subject", table_name="org_users")
    columns = {col["name"] for col in inspector.get_columns("org_users")}
    if "oidc_subject" in columns:
        op.drop_column("org_users", "oidc_subject")
    if "oidc_issuer" in columns:
        op.drop_column("org_users", "oidc_issuer")
