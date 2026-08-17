"""Program 14: Mercury Aviation Network."""

from __future__ import annotations

from alembic import op

revision = "20260814_0017"
down_revision = "20260814_0016"
branch_labels = None
depends_on = None

TABLES = {
    "network_org_profiles",
    "network_professional_profiles",
    "network_partnerships",
    "network_collaborations",
    "network_document_shares",
    "network_message_threads",
    "network_messages",
    "network_events",
    "network_directory_entries",
}


def upgrade() -> None:
    from app.database import Base
    from app.network import models as network_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    for name in (
        "network_directory_entries",
        "network_messages",
        "network_message_threads",
        "network_events",
        "network_document_shares",
        "network_collaborations",
        "network_partnerships",
        "network_professional_profiles",
        "network_org_profiles",
    ):
        op.drop_table(name)
