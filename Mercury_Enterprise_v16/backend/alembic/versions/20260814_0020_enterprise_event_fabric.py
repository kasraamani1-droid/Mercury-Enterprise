"""Program 17: Mercury Enterprise Event Fabric."""

from __future__ import annotations

from alembic import op

revision = "20260814_0020"
down_revision = "20260814_0019"
branch_labels = None
depends_on = None

TABLES = {
    "enterprise_event_types",
    "enterprise_event_store",
    "enterprise_event_subscriptions",
    "enterprise_event_dlq",
    "enterprise_event_replays",
}


def upgrade() -> None:
    from app.database import Base
    from app.event_fabric import models as event_fabric_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    for name in (
        "enterprise_event_replays",
        "enterprise_event_dlq",
        "enterprise_event_subscriptions",
        "enterprise_event_store",
        "enterprise_event_types",
    ):
        op.drop_table(name)
