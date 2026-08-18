"""Sprint 9: maintenance planning, MPD, forecast, AD/SB/EO, MEL, defects."""

from __future__ import annotations

from alembic import op

revision = "20260813_0010"
down_revision = "20260813_0009"
branch_labels = None
depends_on = None

PLANNING_TABLES = {
    "maintenance_programs",
    "maintenance_program_revisions",
    "mpd_tasks",
    "maintenance_checks",
    "airworthiness_directives",
    "service_bulletins",
    "engineering_orders",
    "deferred_defects",
    "mel_items",
    "aircraft_utilization",
    "hangar_plans",
    "parts_plan_lines",
    "tool_plan_lines",
    "workforce_plan_lines",
}


def upgrade() -> None:
    from app.database import Base
    from app.planning import models as planning_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in PLANNING_TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    for name in reversed(
        [
            "workforce_plan_lines",
            "tool_plan_lines",
            "parts_plan_lines",
            "hangar_plans",
            "aircraft_utilization",
            "mel_items",
            "deferred_defects",
            "engineering_orders",
            "service_bulletins",
            "airworthiness_directives",
            "maintenance_checks",
            "mpd_tasks",
            "maintenance_program_revisions",
            "maintenance_programs",
        ]
    ):
        op.drop_table(name)
