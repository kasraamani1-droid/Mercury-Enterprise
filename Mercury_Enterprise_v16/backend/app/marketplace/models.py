"""Program 13 — Mercury Digital Marketplace data model.

B2B aviation commerce platform. Mercury owns the platform; sellers own inventory.
Existing marketplace_listings retained for backward compatibility.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models import uid


def _utcnow() -> datetime:
    return datetime.utcnow()


# Legacy listing types (Program A) — still valid
LISTING_TYPES = (
    "parts",
    "suppliers",
    "tools",
    "calibration",
    "repairs",
    "training",
    "careers",
    "publications",
    "rotables",
    "consumables",
    "expendables",
    "gse",
    "test_equipment",
    "software",
    "consulting",
    "engineering_services",
    "ndt_services",
    "jobs",
)


class MarketplaceListing(Base):
    """Legacy/simple listing row — kept for API compatibility."""

    __tablename__ = "marketplace_listings"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    listing_type: Mapped[str] = mapped_column(String(40), index=True)
    code: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, default="")
    supplier_name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "listing_type", "code", name="uq_mkt_listing"),
        Index("ix_mkt_org_type_status", "organization_id", "listing_type", "status"),
    )


class MarketplaceSeller(Base):
    """Seller digital profile — any org can become a supplier."""

    __tablename__ = "marketplace_sellers"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    seller_type: Mapped[str] = mapped_column(String(80), index=True)
    legal_name: Mapped[str] = mapped_column(String(300))
    display_name: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    contact_email: Mapped[str] = mapped_column(String(200), default="")
    contact_phone: Mapped[str] = mapped_column(String(80), default="")
    locations_json: Mapped[str] = mapped_column(Text, default="[]")
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    certificates_json: Mapped[str] = mapped_column(Text, default="[]")
    approvals_json: Mapped[str] = mapped_column(Text, default="[]")
    # Architecture-only badges — not regulatory verification
    verification_badges_json: Mapped[str] = mapped_column(Text, default="[]")
    verification_disclaimer: Mapped[str] = mapped_column(
        Text,
        default="Badges are platform readiness markers only. Not regulatory verification or approval.",
    )
    rating_avg: Mapped[str] = mapped_column(String(20), default="0")
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_turnaround_days: Mapped[int] = mapped_column(Integer, default=0)
    performance_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "seller_type", "legal_name", name="uq_mkt_seller"),
        Index("ix_mkt_seller_org_status", "organization_id", "status"),
    )


class MarketplaceProduct(Base):
    """Full catalog product / service offering."""

    __tablename__ = "marketplace_products"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    seller_id: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    sku: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(400))
    summary: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    # sale | rental | service | training | job
    offer_mode: Mapped[str] = mapped_column(String(40), default="sale", index=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    qty_available: Mapped[int] = mapped_column(Integer, default=0)
    availability: Mapped[str] = mapped_column(String(40), default="in_stock", index=True)
    serial_tracked: Mapped[str] = mapped_column(String(10), default="false")
    batch_tracked: Mapped[str] = mapped_column(String(10), default="false")
    images_json: Mapped[str] = mapped_column(Text, default="[]")
    documents_json: Mapped[str] = mapped_column(Text, default="[]")
    certificates_json: Mapped[str] = mapped_column(Text, default="[]")  # 8130 / Form 1 / TC release refs
    warranty_json: Mapped[str] = mapped_column(Text, default="{}")
    compatibility_json: Mapped[str] = mapped_column(Text, default="{}")  # aircraft/engines/components
    supersessions_json: Mapped[str] = mapped_column(Text, default="[]")
    alternates_json: Mapped[str] = mapped_column(Text, default="[]")
    publications_json: Mapped[str] = mapped_column(Text, default="[]")
    turnaround_days: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    listing_id: Mapped[str | None] = mapped_column(String(80), nullable=True)  # optional legacy link
    fabric_passport_id: Mapped[str] = mapped_column(String(80), default="")
    ai_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "sku", name="uq_mkt_product_sku"),
        Index("ix_mkt_prod_org_cat", "organization_id", "category", "status"),
        Index("ix_mkt_prod_seller", "seller_id", "status"),
    )


class MarketplaceCartItem(Base):
    __tablename__ = "marketplace_cart_items"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    product_id: Mapped[str] = mapped_column(String(80), index=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "username", "product_id", name="uq_mkt_cart"),
    )


class MarketplaceQuote(Base):
    __tablename__ = "marketplace_quotes"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)  # buyer org
    seller_organization_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    quote_number: Mapped[str] = mapped_column(String(80), index=True)
    product_id: Mapped[str] = mapped_column(String(80), index=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_mkt_quote_org_status", "organization_id", "status"),)


class MarketplaceOrder(Base):
    __tablename__ = "marketplace_orders"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)  # buyer
    seller_organization_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    order_number: Mapped[str] = mapped_column(String(80), index=True)
    quote_id: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    shipping_json: Mapped[str] = mapped_column(Text, default="{}")
    invoice_ref: Mapped[str] = mapped_column(String(120), default="")
    # Future payment gateway — architecture only
    payment_status: Mapped[str] = mapped_column(String(40), default="not_configured")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_mkt_order_org_status", "organization_id", "status"),)


class MarketplaceOrderLine(Base):
    __tablename__ = "marketplace_order_lines"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("marketplace_orders.id"), index=True)
    product_id: Mapped[str] = mapped_column(String(80), index=True)
    sku: Mapped[str] = mapped_column(String(120), default="")
    title: Mapped[str] = mapped_column(String(400), default="")
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))


class MarketplaceReview(Base):
    __tablename__ = "marketplace_reviews"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    seller_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    product_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    rating: Mapped[int] = mapped_column(Integer, default=5)
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    status: Mapped[str] = mapped_column(String(40), default="published", index=True)

    __table_args__ = (Index("ix_mkt_review_target", "seller_id", "product_id"),)


class MarketplaceFavorite(Base):
    __tablename__ = "marketplace_favorites"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    product_id: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "username", "product_id", name="uq_mkt_fav"),
    )


class MarketplaceSavedSearch(Base):
    __tablename__ = "marketplace_saved_searches"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(200))
    query_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
