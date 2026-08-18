"""Sprint 8: work packages, work orders, job cards, attachments."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260813_0009"
down_revision = "20260813_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_packages",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("package_number", sa.String(length=80), nullable=False),
        sa.Column("fleet_id", sa.String(length=80), nullable=True),
        sa.Column("aircraft_id", sa.String(length=80), nullable=False),
        sa.Column("registration", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(), nullable=True),
        sa.Column("scheduled_finish", sa.DateTime(), nullable=True),
        sa.Column("actual_start", sa.DateTime(), nullable=True),
        sa.Column("actual_finish", sa.DateTime(), nullable=True),
        sa.Column("planner_employee_id", sa.String(length=80), nullable=True),
        sa.Column("supervisor_employee_id", sa.String(length=80), nullable=True),
        sa.Column("hangar_bay", sa.String(length=80), nullable=False),
        sa.Column("shift_code", sa.String(length=40), nullable=False),
        sa.Column("estimated_hours", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual_hours", sa.Numeric(12, 2), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "package_number", name="uq_work_package_org_number"),
    )
    op.create_index("ix_work_packages_organization_id", "work_packages", ["organization_id"])
    op.create_index("ix_work_packages_org_status", "work_packages", ["organization_id", "status"])
    op.create_index("ix_work_packages_org_aircraft", "work_packages", ["organization_id", "aircraft_id"])

    op.create_table(
        "work_orders",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("work_package_id", sa.String(length=80), sa.ForeignKey("work_packages.id"), nullable=False),
        sa.Column("wo_number", sa.String(length=80), nullable=False),
        sa.Column("aircraft_id", sa.String(length=80), nullable=False),
        sa.Column("ata_chapter_id", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False),
        sa.Column("planner_employee_id", sa.String(length=80), nullable=True),
        sa.Column("supervisor_employee_id", sa.String(length=80), nullable=True),
        sa.Column("publication_id", sa.String(length=80), nullable=True),
        sa.Column("publication_revision_id", sa.String(length=80), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("estimated_hours", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual_hours", sa.Numeric(12, 2), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "wo_number", name="uq_work_order_org_number"),
    )
    op.create_index("ix_work_orders_organization_id", "work_orders", ["organization_id"])
    op.create_index("ix_work_orders_org_status", "work_orders", ["organization_id", "status"])
    op.create_index("ix_work_orders_package", "work_orders", ["work_package_id"])

    op.create_table(
        "job_cards",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("work_order_id", sa.String(length=80), sa.ForeignKey("work_orders.id"), nullable=False),
        sa.Column("job_card_number", sa.String(length=80), nullable=False),
        sa.Column("maintenance_task_id", sa.String(length=80), nullable=True),
        sa.Column("aircraft_id", sa.String(length=80), nullable=False),
        sa.Column("ata_chapter_id", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False),
        sa.Column("publication_id", sa.String(length=80), nullable=True),
        sa.Column("publication_revision_id", sa.String(length=80), nullable=True),
        sa.Column("component_id", sa.String(length=80), nullable=True),
        sa.Column("required_parts", sa.Text(), nullable=False),
        sa.Column("required_tools", sa.Text(), nullable=False),
        sa.Column("required_skills", sa.Text(), nullable=False),
        sa.Column("required_certification", sa.String(length=200), nullable=False),
        sa.Column("estimated_hours", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual_hours", sa.Numeric(12, 2), nullable=False),
        sa.Column("technician_employee_id", sa.String(length=80), nullable=True),
        sa.Column("inspector_employee_id", sa.String(length=80), nullable=True),
        sa.Column("independent_inspector_employee_id", sa.String(length=80), nullable=True),
        sa.Column("aca_employee_id", sa.String(length=80), nullable=True),
        sa.Column("hangar_bay", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("rework_reason", sa.Text(), nullable=False),
        sa.Column("independent_inspection_required", sa.String(length=10), nullable=False),
        sa.Column("aca_required", sa.String(length=10), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "job_card_number", name="uq_job_card_org_number"),
    )
    op.create_index("ix_job_cards_organization_id", "job_cards", ["organization_id"])
    op.create_index("ix_job_cards_org_status", "job_cards", ["organization_id", "status"])
    op.create_index("ix_job_cards_technician", "job_cards", ["organization_id", "technician_employee_id"])
    op.create_index("ix_job_cards_work_order", "job_cards", ["work_order_id"])

    op.create_table(
        "job_card_attachments",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("job_card_id", sa.String(length=80), sa.ForeignKey("job_cards.id"), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("storage_uri", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_job_card_attachments_card", "job_card_attachments", ["job_card_id"])


def downgrade() -> None:
    op.drop_table("job_card_attachments")
    op.drop_table("job_cards")
    op.drop_table("work_orders")
    op.drop_table("work_packages")
