"""Maintenance task engine fields linked to technical library."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260813_0007"
down_revision = "20260813_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "maintenance_tasks",
        sa.Column("task_number", sa.String(length=80), nullable=False, server_default=""),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column("task_type", sa.String(length=40), nullable=False, server_default="corrective"),
    )
    op.add_column("maintenance_tasks", sa.Column("fleet_id", sa.String(length=80), nullable=True))
    op.add_column(
        "maintenance_tasks",
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="normal"),
    )
    op.add_column("maintenance_tasks", sa.Column("due_date", sa.DateTime(), nullable=True))
    op.add_column(
        "maintenance_tasks",
        sa.Column("estimated_hours", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column("actual_hours", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column("required_parts", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column("required_tools", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column("required_skills", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column("required_certification", sa.String(length=200), nullable=False, server_default=""),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column("requires_inspector", sa.String(length=10), nullable=False, server_default="true"),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column(
            "independent_inspection_required",
            sa.String(length=10),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column("aca_required", sa.String(length=10), nullable=False, server_default="false"),
    )
    op.add_column(
        "maintenance_tasks",
        sa.Column("release_status", sa.String(length=40), nullable=False, server_default="not_released"),
    )

    # Backfill unique task numbers from id when empty.
    op.execute(
        sa.text(
            "UPDATE maintenance_tasks SET task_number = 'MT-' || UPPER(SUBSTR(id, 1, 12)) "
            "WHERE task_number = '' OR task_number IS NULL"
        )
    )

    op.create_unique_constraint(
        "uq_maintenance_task_org_number", "maintenance_tasks", ["organization_id", "task_number"]
    )
    op.create_index("ix_maintenance_tasks_task_number", "maintenance_tasks", ["task_number"])
    op.create_index("ix_maintenance_tasks_task_type", "maintenance_tasks", ["task_type"])
    op.create_index("ix_maintenance_tasks_fleet_id", "maintenance_tasks", ["fleet_id"])
    op.create_index("ix_maintenance_tasks_priority", "maintenance_tasks", ["priority"])
    op.create_index("ix_maintenance_tasks_due_date", "maintenance_tasks", ["due_date"])
    op.create_index("ix_maintenance_tasks_publication_id", "maintenance_tasks", ["publication_id"])
    op.create_index(
        "ix_maintenance_tasks_publication_revision_id",
        "maintenance_tasks",
        ["publication_revision_id"],
    )
    op.create_index("ix_maintenance_tasks_component_id", "maintenance_tasks", ["component_id"])
    op.create_index("ix_maintenance_tasks_release_status", "maintenance_tasks", ["release_status"])
    op.create_index("ix_maintenance_tasks_org_type", "maintenance_tasks", ["organization_id", "task_type"])
    op.create_index(
        "ix_maintenance_tasks_org_priority", "maintenance_tasks", ["organization_id", "priority"]
    )
    op.create_index("ix_maintenance_tasks_org_fleet", "maintenance_tasks", ["organization_id", "fleet_id"])
    op.create_index("ix_maintenance_tasks_org_pub", "maintenance_tasks", ["organization_id", "publication_id"])

    op.alter_column("maintenance_tasks", "task_number", server_default=None)
    op.alter_column("maintenance_tasks", "task_type", server_default=None)
    op.alter_column("maintenance_tasks", "priority", server_default=None)
    op.alter_column("maintenance_tasks", "estimated_hours", server_default=None)
    op.alter_column("maintenance_tasks", "actual_hours", server_default=None)
    op.alter_column("maintenance_tasks", "required_parts", server_default=None)
    op.alter_column("maintenance_tasks", "required_tools", server_default=None)
    op.alter_column("maintenance_tasks", "required_skills", server_default=None)
    op.alter_column("maintenance_tasks", "required_certification", server_default=None)
    op.alter_column("maintenance_tasks", "requires_inspector", server_default=None)
    op.alter_column("maintenance_tasks", "independent_inspection_required", server_default=None)
    op.alter_column("maintenance_tasks", "aca_required", server_default=None)
    op.alter_column("maintenance_tasks", "release_status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_maintenance_tasks_org_pub", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_org_fleet", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_org_priority", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_org_type", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_release_status", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_component_id", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_publication_revision_id", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_publication_id", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_due_date", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_priority", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_fleet_id", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_task_type", table_name="maintenance_tasks")
    op.drop_index("ix_maintenance_tasks_task_number", table_name="maintenance_tasks")
    op.drop_constraint("uq_maintenance_task_org_number", "maintenance_tasks", type_="unique")
    for col in (
        "release_status",
        "aca_required",
        "independent_inspection_required",
        "requires_inspector",
        "required_certification",
        "required_skills",
        "required_tools",
        "required_parts",
        "actual_hours",
        "estimated_hours",
        "due_date",
        "priority",
        "fleet_id",
        "task_type",
        "task_number",
    ):
        op.drop_column("maintenance_tasks", col)
