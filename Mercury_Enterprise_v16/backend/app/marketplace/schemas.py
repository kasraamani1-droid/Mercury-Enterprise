"""Program 13 — Marketplace schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


class ListingCreate(BaseModel):
    organization_id: str | None = None
    listing_type: str = Field(min_length=1, max_length=40)
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    summary: str = ""
    supplier_name: str = ""


class ListingOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    listing_type: str
    code: str
    title: str
    summary: str
    supplier_name: str
    status: str
    ai_metadata_json: str
    created_at: datetime


class SellerCreate(BaseModel):
    organization_id: str | None = None
    seller_type: str = Field(min_length=1, max_length=80)
    legal_name: str = Field(min_length=1, max_length=300)
    display_name: str = ""
    summary: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    locations_json: str = "[]"
    capabilities_json: str = "[]"
    certificates_json: str = "[]"
    approvals_json: str = "[]"
    verification_badges_json: str = "[]"


class SellerOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    seller_type: str
    legal_name: str
    display_name: str
    summary: str
    contact_email: str
    contact_phone: str
    locations_json: str
    capabilities_json: str
    certificates_json: str
    approvals_json: str
    verification_badges_json: str
    verification_disclaimer: str
    rating_avg: str
    review_count: int
    avg_turnaround_days: int
    status: str
    created_at: datetime


class ProductCreate(BaseModel):
    organization_id: str | None = None
    seller_id: str
    category: str = Field(min_length=1, max_length=80)
    sku: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=400)
    summary: str = ""
    description: str = ""
    offer_mode: str = Field(default="sale", pattern="^(sale|rental|service|training|job)$")
    currency: str = "USD"
    unit_price: Decimal = Decimal("0")
    qty_available: int = Field(default=0, ge=0)
    availability: str = "in_stock"
    serial_tracked: bool = False
    batch_tracked: bool = False
    images_json: str = "[]"
    documents_json: str = "[]"
    certificates_json: str = "[]"
    warranty_json: str = "{}"
    compatibility_json: str = "{}"
    supersessions_json: str = "[]"
    alternates_json: str = "[]"
    publications_json: str = "[]"
    turnaround_days: int = 0
    status: str = "published"


class ProductOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    seller_id: str
    category: str
    sku: str
    title: str
    summary: str
    description: str
    offer_mode: str
    currency: str
    unit_price: Decimal
    qty_available: int
    availability: str
    serial_tracked: str
    batch_tracked: str
    certificates_json: str
    warranty_json: str
    compatibility_json: str
    supersessions_json: str
    alternates_json: str
    publications_json: str
    turnaround_days: int
    status: str
    ai_metadata_json: str
    created_at: datetime


class CartItemCreate(BaseModel):
    organization_id: str | None = None
    product_id: str
    qty: int = Field(default=1, ge=1)
    notes: str = ""


class CartItemOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    username: str
    product_id: str
    qty: int
    notes: str
    created_at: datetime


class QuoteCreate(BaseModel):
    organization_id: str | None = None
    product_id: str
    qty: int = Field(default=1, ge=1)
    notes: str = ""


class QuoteOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    seller_organization_id: str
    quote_number: str
    product_id: str
    qty: int
    unit_price: Decimal
    currency: str
    status: str
    notes: str
    created_at: datetime


class OrderCreate(BaseModel):
    organization_id: str | None = None
    quote_id: str | None = None
    product_id: str | None = None
    qty: int = Field(default=1, ge=1)
    notes: str = ""
    shipping_json: str = "{}"


class OrderLineOut(BaseModel):
    model_config = ORM

    id: str
    order_id: str
    product_id: str
    sku: str
    title: str
    qty: int
    unit_price: Decimal
    line_total: Decimal


class OrderOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    seller_organization_id: str
    order_number: str
    quote_id: str
    status: str
    currency: str
    total_amount: Decimal
    shipping_json: str
    invoice_ref: str
    payment_status: str
    notes: str
    created_at: datetime
    lines: list[OrderLineOut] = []


class ReviewCreate(BaseModel):
    organization_id: str | None = None
    seller_id: str = ""
    product_id: str = ""
    rating: int = Field(default=5, ge=1, le=5)
    title: str = ""
    body: str = ""


class ReviewOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    seller_id: str
    product_id: str
    rating: int
    title: str
    body: str
    created_by: str
    created_at: datetime


class FavoriteCreate(BaseModel):
    organization_id: str | None = None
    product_id: str


class FavoriteOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    username: str
    product_id: str
    created_at: datetime


class SavedSearchCreate(BaseModel):
    organization_id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    query_json: str = "{}"


class SavedSearchOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    username: str
    name: str
    query_json: str
    created_at: datetime


class CatalogCategoryOut(BaseModel):
    code: str
    name: str
    family: str


class MarketplaceOverviewOut(BaseModel):
    organization_id: str
    listings: int
    sellers: int
    products: int
    quotes: int
    orders: int
    reviews: int
    categories: int


class ProductSearchResponse(BaseModel):
    query: str
    total: int
    items: list[ProductOut]


class PricingOut(BaseModel):
    product_id: str
    sku: str
    currency: str
    unit_price: Decimal
    offer_mode: str
    availability: str
    qty_available: int


class InventoryOut(BaseModel):
    product_id: str
    sku: str
    qty_available: int
    availability: str
    serial_tracked: str
    batch_tracked: str
