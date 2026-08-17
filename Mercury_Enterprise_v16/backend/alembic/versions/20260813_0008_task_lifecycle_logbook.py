"""Task lifecycle versioning and independent inspector on technical log."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260813_0008"
down_revision = "20260813_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "maintenance_tasks",
        sa.Column("assigned_to_employee_id", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_maintenance_tasks_assigned_to_employee_id",
        "maintenance_tasks",
        ["assigned_to_employee_id"],
    )
    with op.batch_alter_table("maintenance_tasks") as batch_op:
        batch_op.alter_column("version", server_default=None)

    op.add_column(
        "technical_log_entries",
        sa.Column("independent_inspector_employee_id", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("technical_log_entries", "independent_inspector_employee_id")
    op.drop_index("ix_maintenance_tasks_assigned_to_employee_id", table_name="maintenance_tasks")
    with op.batch_alter_table("maintenance_tasks") as batch_op:
        batch_op.drop_column("version")
        batch_op.drop_column("assigned_to_employee_id")
