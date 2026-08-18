"""Program 13: Mercury Digital Marketplace commerce tables."""

from __future__ import annotations

from alembic import op

revision = "20260814_0016"
down_revision = "20260814_0015"
branch_labels = None
depends_on = None

TABLES = {
    "marketplace_sellers",
    "marketplace_products",
    "marketplace_cart_items",
    "marketplace_quotes",
    "marketplace_orders",
    "marketplace_order_lines",
    "marketplace_reviews",
    "marketplace_favorites",
    "marketplace_saved_searches",
}


def upgrade() -> None:
    from app.database import Base
    from app.marketplace import models as marketplace_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    for name in (
        "marketplace_saved_searches",
        "marketplace_favorites",
        "marketplace_reviews",
        "marketplace_order_lines",
        "marketplace_orders",
        "marketplace_quotes",
        "marketplace_cart_items",
        "marketplace_products",
        "marketplace_sellers",
    ):
        op.drop_table(name)
