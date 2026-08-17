"""Program 16: Mercury Plugin Platform."""

from __future__ import annotations

from alembic import op

revision = "20260814_0019"
down_revision = "20260814_0018"
branch_labels = None
depends_on = None

TABLES = {
    "plugin_definitions",
    "plugin_installations",
    "plugin_dashboard_layouts",
}


def upgrade() -> None:
    from app.database import Base
    from app.plugins import models as plugin_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    for name in ("plugin_dashboard_layouts", "plugin_installations", "plugin_definitions"):
        op.drop_table(name)
