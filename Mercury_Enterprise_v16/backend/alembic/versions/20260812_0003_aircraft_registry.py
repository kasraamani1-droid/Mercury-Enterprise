"""Aircraft registry & fleet management tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260812_0003"
down_revision = "20260812_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manufacturers",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_manufacturers_name", "manufacturers", ["name"], unique=True)
    op.create_index("ix_manufacturers_code", "manufacturers", ["code"], unique=True)
    op.create_index("ix_manufacturers_status", "manufacturers", ["status"])

    op.create_table(
        "aircraft_models",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("manufacturer_id", sa.String(length=80), sa.ForeignKey("manufacturers.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("icao_type", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("engine_count", sa.Integer(), nullable=False),
        sa.Column("max_seats", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("manufacturer_id", "code", name="uq_aircraft_model_mfr_code"),
    )
    op.create_index("ix_aircraft_models_manufacturer_id", "aircraft_models", ["manufacturer_id"])
    op.create_index("ix_aircraft_models_name", "aircraft_models", ["name"])
    op.create_index("ix_aircraft_models_code", "aircraft_models", ["code"])
    op.create_index("ix_aircraft_models_icao_type", "aircraft_models", ["icao_type"])
    op.create_index("ix_aircraft_models_status", "aircraft_models", ["status"])

    op.create_table(
        "aircraft_statuses",
        sa.Column("code", sa.String(length=40), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_operational", sa.String(length=10), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_aircraft_statuses_name", "aircraft_statuses", ["name"], unique=True)
    op.create_index("ix_aircraft_statuses_is_operational", "aircraft_statuses", ["is_operational"])
    op.create_index("ix_aircraft_statuses_status", "aircraft_statuses", ["status"])

    op.create_table(
        "fleet_operators",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("icao_code", sa.String(length=10), nullable=False),
        sa.Column("iata_code", sa.String(length=10), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_fleet_operator_org_code"),
    )
    op.create_index("ix_fleet_operators_organization_id", "fleet_operators", ["organization_id"])
    op.create_index("ix_fleet_operators_icao_code", "fleet_operators", ["icao_code"])
    op.create_index("ix_fleet_operators_status", "fleet_operators", ["status"])
    op.create_index("ix_fleet_operators_org_status", "fleet_operators", ["organization_id", "status"])

    op.create_table(
        "fleets",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("operator_id", sa.String(length=80), sa.ForeignKey("fleet_operators.id"), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("base_site_id", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_fleet_org_code"),
    )
    op.create_index("ix_fleets_organization_id", "fleets", ["organization_id"])
    op.create_index("ix_fleets_operator_id", "fleets", ["operator_id"])
    op.create_index("ix_fleets_base_site_id", "fleets", ["base_site_id"])
    op.create_index("ix_fleets_status", "fleets", ["status"])
    op.create_index("ix_fleets_org_status", "fleets", ["organization_id", "status"])

    op.create_table(
        "aircraft",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("model_id", sa.String(length=80), sa.ForeignKey("aircraft_models.id"), nullable=False),
        sa.Column("fleet_id", sa.String(length=80), sa.ForeignKey("fleets.id"), nullable=True),
        sa.Column("operator_id", sa.String(length=80), sa.ForeignKey("fleet_operators.id"), nullable=True),
        sa.Column("status_code", sa.String(length=40), sa.ForeignKey("aircraft_statuses.code"), nullable=False),
        sa.Column("serial_number", sa.String(length=120), nullable=False),
        sa.Column("manufacturer_serial", sa.String(length=120), nullable=False),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("home_base_site_id", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "serial_number", name="uq_aircraft_org_serial"),
    )
    op.create_index("ix_aircraft_organization_id", "aircraft", ["organization_id"])
    op.create_index("ix_aircraft_model_id", "aircraft", ["model_id"])
    op.create_index("ix_aircraft_fleet_id", "aircraft", ["fleet_id"])
    op.create_index("ix_aircraft_operator_id", "aircraft", ["operator_id"])
    op.create_index("ix_aircraft_status_code", "aircraft", ["status_code"])
    op.create_index("ix_aircraft_serial_number", "aircraft", ["serial_number"])
    op.create_index("ix_aircraft_home_base_site_id", "aircraft", ["home_base_site_id"])
    op.create_index("ix_aircraft_status", "aircraft", ["status"])
    op.create_index("ix_aircraft_org_status", "aircraft", ["organization_id", "status"])
    op.create_index("ix_aircraft_org_status_code", "aircraft", ["organization_id", "status_code"])

    op.create_table(
        "registrations",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("aircraft_id", sa.String(length=80), sa.ForeignKey("aircraft.id"), nullable=False),
        sa.Column("registration_mark", sa.String(length=40), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("is_current", sa.String(length=10), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=True),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("registration_mark", name="uq_registration_mark"),
    )
    op.create_index("ix_registrations_organization_id", "registrations", ["organization_id"])
    op.create_index("ix_registrations_aircraft_id", "registrations", ["aircraft_id"])
    op.create_index("ix_registrations_registration_mark", "registrations", ["registration_mark"])
    op.create_index("ix_registrations_is_current", "registrations", ["is_current"])
    op.create_index("ix_registrations_status", "registrations", ["status"])
    op.create_index("ix_registrations_org_aircraft", "registrations", ["organization_id", "aircraft_id"])
    op.create_index("ix_registrations_org_current", "registrations", ["organization_id", "is_current"])


def downgrade() -> None:
    op.drop_table("registrations")
    op.drop_table("aircraft")
    op.drop_table("fleets")
    op.drop_table("fleet_operators")
    op.drop_table("aircraft_statuses")
    op.drop_table("aircraft_models")
    op.drop_table("manufacturers")
