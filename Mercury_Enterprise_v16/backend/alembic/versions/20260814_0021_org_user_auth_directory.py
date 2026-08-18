"""Durable operator directory: persist platform_role; widen password_hash for Argon2id."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260814_0021"
down_revision = "20260814_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "org_users" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("org_users")}
    if "platform_role" not in columns:
        op.add_column(
            "org_users",
            sa.Column("platform_role", sa.String(length=40), nullable=False, server_default=""),
        )
    if "password_hash" in columns and bind.dialect.name != "sqlite":
        op.alter_column(
            "org_users",
            "password_hash",
            existing_type=sa.String(length=128),
            type_=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "org_users" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("org_users")}
    if "platform_role" in columns:
        op.drop_column("org_users", "platform_role")
    if "password_hash" in columns and bind.dialect.name != "sqlite":
        op.alter_column(
            "org_users",
            "password_hash",
            existing_type=sa.String(length=255),
            type_=sa.String(length=128),
            existing_nullable=False,
        )
