"""Program 11: Mercury Universal Data Fabric tables."""

from __future__ import annotations

from alembic import op

revision = "20260814_0014"
down_revision = "20260814_0013"
branch_labels = None
depends_on = None

FABRIC_TABLES = {
    "fabric_entity_types",
    "fabric_passports",
    "fabric_passport_history",
    "fabric_relationships",
    "fabric_events",
    "fabric_tags",
    "fabric_attachment_refs",
    "fabric_retention_policies",
    "fabric_legal_holds",
}


def upgrade() -> None:
    from app.database import Base
    from app.fabric import models as fabric_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in FABRIC_TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    for name in (
        "fabric_legal_holds",
        "fabric_retention_policies",
        "fabric_attachment_refs",
        "fabric_tags",
        "fabric_events",
        "fabric_relationships",
        "fabric_passport_history",
        "fabric_passports",
        "fabric_entity_types",
    ):
        op.drop_table(name)
