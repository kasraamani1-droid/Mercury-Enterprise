"""Program 15: Mercury Digital Twin."""

from __future__ import annotations

from alembic import op

revision = "20260814_0018"
down_revision = "20260814_0017"
branch_labels = None
depends_on = None

TABLES = {
    "twin_objects",
    "twin_history_entries",
    "twin_configurations",
    "twin_reliability_snapshots",
    "twin_search_entries",
}


def upgrade() -> None:
    from app.database import Base
    from app.twin import models as twin_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    for name in (
        "twin_search_entries",
        "twin_reliability_snapshots",
        "twin_configurations",
        "twin_history_entries",
        "twin_objects",
    ):
        op.drop_table(name)
