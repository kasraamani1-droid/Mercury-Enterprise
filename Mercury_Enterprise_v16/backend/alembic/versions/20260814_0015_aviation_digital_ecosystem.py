"""Program 12: Aviation Digital Ecosystem + Mercury Connect."""

from __future__ import annotations

from alembic import op

revision = "20260814_0015"
down_revision = "20260814_0014"
branch_labels = None
depends_on = None

TABLES = {
    "ecosystem_definitions",
    "ecosystem_capabilities",
    "ecosystem_enrollments",
    "connect_connectors",
    "connect_bindings",
}


def upgrade() -> None:
    from app.database import Base
    from app.ecosystem import models as ecosystem_models  # noqa: F401
    from app.connect import models as connect_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    for name in (
        "connect_bindings",
        "connect_connectors",
        "ecosystem_enrollments",
        "ecosystem_capabilities",
        "ecosystem_definitions",
    ):
        op.drop_table(name)
