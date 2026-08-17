"""AEOS readiness domains: marketplace, OEM, authority + AI search metadata."""

from __future__ import annotations

from alembic import op

revision = "20260814_0013"
down_revision = "20260813_0012"
branch_labels = None
depends_on = None

TABLES = {
    "marketplace_listings",
    "oem_manufacturers",
    "authority_bodies",
}


def upgrade() -> None:
    from app.database import Base
    from app.marketplace import models as marketplace_models  # noqa: F401
    from app.oem import models as oem_models  # noqa: F401
    from app.authority import models as authority_models  # noqa: F401
    from app.platform import models as platform_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)

    # Additive AI metadata column on existing search documents.
    try:
        op.execute(
            "ALTER TABLE platform_search_documents ADD COLUMN IF NOT EXISTS ai_metadata_json TEXT DEFAULT '{}'"
        )
    except Exception:
        # SQLite older variants: try without IF NOT EXISTS
        try:
            op.execute(
                "ALTER TABLE platform_search_documents ADD COLUMN ai_metadata_json TEXT DEFAULT '{}'"
            )
        except Exception:
            pass


def downgrade() -> None:
    for name in ("marketplace_listings", "oem_manufacturers", "authority_bodies"):
        op.drop_table(name)
