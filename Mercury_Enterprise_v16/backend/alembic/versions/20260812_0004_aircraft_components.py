"""Aircraft components & configuration management tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260812_0004"
down_revision = "20260812_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ata_chapters",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("chapter_number", sa.String(length=10), nullable=False),
        sa.Column("subchapter", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("chapter_number", "subchapter", name="uq_ata_chapter_sub"),
    )
    op.create_index("ix_ata_chapters_chapter_number", "ata_chapters", ["chapter_number"])
    op.create_index("ix_ata_chapters_subchapter", "ata_chapters", ["subchapter"])
    op.create_index("ix_ata_chapters_status", "ata_chapters", ["status"])

    op.create_table(
        "component_catalog",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("part_number", sa.String(length=120), nullable=False),
        sa.Column("manufacturer_id", sa.String(length=80), sa.ForeignKey("manufacturers.id"), nullable=True),
        sa.Column("oem_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=400), nullable=False),
        sa.Column("ata_chapter_id", sa.String(length=80), sa.ForeignKey("ata_chapters.id"), nullable=True),
        sa.Column("component_type", sa.String(length=40), nullable=False),
        sa.Column("is_serialized", sa.String(length=10), nullable=False),
        sa.Column("is_life_limited", sa.String(length=10), nullable=False),
        sa.Column("hour_limit", sa.Numeric(12, 2), nullable=True),
        sa.Column("cycle_limit", sa.Integer(), nullable=True),
        sa.Column("calendar_limit_days", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_component_catalog_part_number", "component_catalog", ["part_number"], unique=True)
    op.create_index("ix_component_catalog_manufacturer_id", "component_catalog", ["manufacturer_id"])
    op.create_index("ix_component_catalog_ata_chapter_id", "component_catalog", ["ata_chapter_id"])
    op.create_index("ix_component_catalog_component_type", "component_catalog", ["component_type"])
    op.create_index("ix_component_catalog_is_serialized", "component_catalog", ["is_serialized"])
    op.create_index("ix_component_catalog_is_life_limited", "component_catalog", ["is_life_limited"])
    op.create_index("ix_component_catalog_status", "component_catalog", ["status"])

    op.create_table(
        "serialized_components",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("catalog_item_id", sa.String(length=80), sa.ForeignKey("component_catalog.id"), nullable=False),
        sa.Column("serial_number", sa.String(length=120), nullable=False),
        sa.Column("manufacturer_name", sa.String(length=200), nullable=False),
        sa.Column("component_status", sa.String(length=40), nullable=False),
        sa.Column("current_aircraft_id", sa.String(length=80), sa.ForeignKey("aircraft.id"), nullable=True),
        sa.Column("installation_position", sa.String(length=80), nullable=True),
        sa.Column("date_installed", sa.DateTime(), nullable=True),
        sa.Column("date_removed", sa.DateTime(), nullable=True),
        sa.Column("tsn_hours", sa.Numeric(12, 2), nullable=False),
        sa.Column("csn_cycles", sa.Integer(), nullable=False),
        sa.Column("tso_hours", sa.Numeric(12, 2), nullable=False),
        sa.Column("cso_cycles", sa.Integer(), nullable=False),
        sa.Column("aircraft_hours_at_install", sa.Numeric(12, 2), nullable=True),
        sa.Column("aircraft_cycles_at_install", sa.Integer(), nullable=True),
        sa.Column("hour_limit", sa.Numeric(12, 2), nullable=True),
        sa.Column("cycle_limit", sa.Integer(), nullable=True),
        sa.Column("calendar_limit_days", sa.Integer(), nullable=True),
        sa.Column("remaining_hours", sa.Numeric(12, 2), nullable=True),
        sa.Column("remaining_cycles", sa.Integer(), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "serial_number", name="uq_component_org_serial"),
        sa.UniqueConstraint("current_aircraft_id", "installation_position", name="uq_aircraft_position_occupant"),
    )
    op.create_index("ix_serialized_components_organization_id", "serialized_components", ["organization_id"])
    op.create_index("ix_serialized_components_catalog_item_id", "serialized_components", ["catalog_item_id"])
    op.create_index("ix_serialized_components_serial_number", "serialized_components", ["serial_number"])
    op.create_index("ix_serialized_components_component_status", "serialized_components", ["component_status"])
    op.create_index("ix_serialized_components_current_aircraft_id", "serialized_components", ["current_aircraft_id"])
    op.create_index("ix_serialized_components_installation_position", "serialized_components", ["installation_position"])
    op.create_index("ix_serialized_components_status", "serialized_components", ["status"])
    op.create_index("ix_serialized_components_org_status", "serialized_components", ["organization_id", "component_status"])
    op.create_index("ix_serialized_components_org_aircraft", "serialized_components", ["organization_id", "current_aircraft_id"])
    op.create_index("ix_serialized_components_org_catalog", "serialized_components", ["organization_id", "catalog_item_id"])

    op.create_table(
        "component_installation_history",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("component_id", sa.String(length=80), sa.ForeignKey("serialized_components.id"), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("aircraft_id", sa.String(length=80), nullable=True),
        sa.Column("from_aircraft_id", sa.String(length=80), nullable=True),
        sa.Column("to_aircraft_id", sa.String(length=80), nullable=True),
        sa.Column("position", sa.String(length=80), nullable=True),
        sa.Column("from_status", sa.String(length=40), nullable=False),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("aircraft_hours", sa.Numeric(12, 2), nullable=True),
        sa.Column("aircraft_cycles", sa.Integer(), nullable=True),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.String(length=400), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_component_installation_history_organization_id", "component_installation_history", ["organization_id"])
    op.create_index("ix_component_installation_history_component_id", "component_installation_history", ["component_id"])
    op.create_index("ix_component_installation_history_event_type", "component_installation_history", ["event_type"])
    op.create_index("ix_component_installation_history_aircraft_id", "component_installation_history", ["aircraft_id"])
    op.create_index("ix_component_installation_history_from_aircraft_id", "component_installation_history", ["from_aircraft_id"])
    op.create_index("ix_component_installation_history_to_aircraft_id", "component_installation_history", ["to_aircraft_id"])
    op.create_index("ix_component_installation_history_occurred_at", "component_installation_history", ["occurred_at"])
    op.create_index("ix_comp_hist_org_component", "component_installation_history", ["organization_id", "component_id"])
    op.create_index("ix_comp_hist_org_aircraft", "component_installation_history", ["organization_id", "aircraft_id"])
    op.create_index("ix_comp_hist_org_event", "component_installation_history", ["organization_id", "event_type"])


def downgrade() -> None:
    op.drop_table("component_installation_history")
    op.drop_table("serialized_components")
    op.drop_table("component_catalog")
    op.drop_table("ata_chapters")
