"""Durable tenant-scoped approval_requests table (RC1 Blocker 03)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260814_0022"
down_revision = "20260814_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "approval_requests" in inspector.get_table_names():
        return
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=120), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("requested_by", sa.String(length=120), nullable=False),
        sa.Column("requested_role", sa.String(length=40), nullable=False),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("site_id", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_approval_requests_action", "approval_requests", ["action"])
    op.create_index("ix_approval_requests_target_id", "approval_requests", ["target_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_organization_id", "approval_requests", ["organization_id"])
    op.create_index("ix_approval_requests_site_id", "approval_requests", ["site_id"])
    op.create_index("ix_approval_requests_created_at", "approval_requests", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "approval_requests" not in inspector.get_table_names():
        return
    op.drop_index("ix_approval_requests_created_at", table_name="approval_requests")
    op.drop_index("ix_approval_requests_site_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_organization_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_target_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_action", table_name="approval_requests")
    op.drop_table("approval_requests")
