"""Program 13 — Mercury Digital Marketplace HTTP API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from ..shared import ActorContext
from .schemas import (
    CartItemCreate,
    CartItemOut,
    CatalogCategoryOut,
    FavoriteCreate,
    FavoriteOut,
    InventoryOut,
    ListingCreate,
    ListingOut,
    MarketplaceOverviewOut,
    OrderCreate,
    OrderOut,
    PricingOut,
    ProductCreate,
    ProductOut,
    ProductSearchResponse,
    QuoteCreate,
    QuoteOut,
    ReviewCreate,
    ReviewOut,
    SavedSearchCreate,
    SavedSearchOut,
    SellerCreate,
    SellerOut,
)
from .service import MarketplaceService

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])
Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_marketplace_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("marketplace.read", "platform.read", "org.read"),
        any_of=True,
        detail="Marketplace read required",
    )
    return session


def require_marketplace_manage(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("marketplace.manage", "platform.manage"),
        any_of=True,
        detail="Marketplace manage required",
    )
    return session


def _actor(session: Session_) -> ActorContext:
    return ActorContext(
        username=str(session["operator"]),
        role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )


@router.get("/overview", response_model=MarketplaceOverviewOut)
def marketplace_overview(
    organization_id: str | None = None,
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> MarketplaceOverviewOut:
    return MarketplaceService(db).overview(_actor(session), organization_id)


@router.get("/categories", response_model=list[CatalogCategoryOut])
def list_categories(
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> list[CatalogCategoryOut]:
    _ = session
    return [CatalogCategoryOut(**c) for c in MarketplaceService(db).categories()]


@router.get("/listings", response_model=list[ListingOut])
def list_listings(
    organization_id: str | None = None,
    listing_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> list[ListingOut]:
    rows = MarketplaceService(db).list(
        _actor(session),
        organization_id=organization_id,
        listing_type=listing_type,
        limit=limit,
        offset=offset,
    )
    return [ListingOut.model_validate(r) for r in rows]


@router.post("/listings", response_model=ListingOut, status_code=201)
def create_listing(
    payload: ListingCreate,
    session: Session_ = Depends(require_marketplace_manage),
    db: Session = Depends(get_db),
) -> ListingOut:
    row = MarketplaceService(db).create(
        _actor(session),
        listing_type=payload.listing_type,
        code=payload.code,
        title=payload.title,
        summary=payload.summary,
        supplier_name=payload.supplier_name,
        organization_id=payload.organization_id,
    )
    return ListingOut.model_validate(row)


@router.get("/sellers", response_model=list[SellerOut])
def list_sellers(
    organization_id: str | None = None,
    seller_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> list[SellerOut]:
    rows = MarketplaceService(db).list_sellers(
        _actor(session),
        organization_id=organization_id,
        seller_type=seller_type,
        limit=limit,
        offset=offset,
    )
    return [SellerOut.model_validate(r) for r in rows]


@router.post("/sellers", response_model=SellerOut, status_code=201)
def create_seller(
    payload: SellerCreate,
    session: Session_ = Depends(require_marketplace_manage),
    db: Session = Depends(get_db),
) -> SellerOut:
    row = MarketplaceService(db).create_seller(
        _actor(session),
        seller_type=payload.seller_type,
        legal_name=payload.legal_name,
        display_name=payload.display_name,
        summary=payload.summary,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        locations_json=payload.locations_json,
        capabilities_json=payload.capabilities_json,
        certificates_json=payload.certificates_json,
        approvals_json=payload.approvals_json,
        verification_badges_json=payload.verification_badges_json,
        organization_id=payload.organization_id,
    )
    return SellerOut.model_validate(row)


@router.get("/sellers/{seller_id}", response_model=SellerOut)
def get_seller(
    seller_id: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> SellerOut:
    row = MarketplaceService(db).get_seller(_actor(session), seller_id, organization_id)
    return SellerOut.model_validate(row)


@router.get("/products", response_model=list[ProductOut])
def list_products(
    organization_id: str | None = None,
    category: str | None = None,
    seller_id: str | None = None,
    offer_mode: str | None = None,
    status_filter: str | None = Query("published", alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> list[ProductOut]:
    rows = MarketplaceService(db).list_products(
        _actor(session),
        organization_id=organization_id,
        category=category,
        seller_id=seller_id,
        offer_mode=offer_mode,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [ProductOut.model_validate(r) for r in rows]


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    session: Session_ = Depends(require_marketplace_manage),
    db: Session = Depends(get_db),
) -> ProductOut:
    row = MarketplaceService(db).create_product(
        _actor(session),
        seller_id=payload.seller_id,
        category=payload.category,
        sku=payload.sku,
        title=payload.title,
        summary=payload.summary,
        description=payload.description,
        offer_mode=payload.offer_mode,
        currency=payload.currency,
        unit_price=payload.unit_price,
        qty_available=payload.qty_available,
        availability=payload.availability,
        serial_tracked=payload.serial_tracked,
        batch_tracked=payload.batch_tracked,
        images_json=payload.images_json,
        documents_json=payload.documents_json,
        certificates_json=payload.certificates_json,
        warranty_json=payload.warranty_json,
        compatibility_json=payload.compatibility_json,
        supersessions_json=payload.supersessions_json,
        alternates_json=payload.alternates_json,
        publications_json=payload.publications_json,
        turnaround_days=payload.turnaround_days,
        status=payload.status,
        organization_id=payload.organization_id,
    )
    return ProductOut.model_validate(row)


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(
    product_id: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> ProductOut:
    row = MarketplaceService(db).get_product(_actor(session), product_id, organization_id)
    return ProductOut.model_validate(row)


@router.get("/products/{product_id}/pricing", response_model=PricingOut)
def product_pricing(
    product_id: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> PricingOut:
    row = MarketplaceService(db).get_product(_actor(session), product_id, organization_id)
    return PricingOut(
        product_id=row.id,
        sku=row.sku,
        currency=row.currency,
        unit_price=row.unit_price,
        offer_mode=row.offer_mode,
        availability=row.availability,
        qty_available=row.qty_available,
    )


@router.get("/products/{product_id}/inventory", response_model=InventoryOut)
def product_inventory(
    product_id: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> InventoryOut:
    row = MarketplaceService(db).get_product(_actor(session), product_id, organization_id)
    return InventoryOut(
        product_id=row.id,
        sku=row.sku,
        qty_available=row.qty_available,
        availability=row.availability,
        serial_tracked=row.serial_tracked,
        batch_tracked=row.batch_tracked,
    )


@router.get("/search", response_model=ProductSearchResponse)
def search_products(
    q: str = "",
    category: str | None = None,
    organization_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> ProductSearchResponse:
    return MarketplaceService(db).search_products(
        _actor(session),
        q=q,
        category=category,
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )


@router.get("/cart", response_model=list[CartItemOut])
def list_cart(
    organization_id: str | None = None,
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> list[CartItemOut]:
    rows = MarketplaceService(db).list_cart(_actor(session), organization_id=organization_id)
    return [CartItemOut.model_validate(r) for r in rows]


@router.post("/cart", response_model=CartItemOut, status_code=201)
def add_cart(
    payload: CartItemCreate,
    session: Session_ = Depends(require_marketplace_manage),
    db: Session = Depends(get_db),
) -> CartItemOut:
    row = MarketplaceService(db).add_cart_item(
        _actor(session),
        product_id=payload.product_id,
        qty=payload.qty,
        notes=payload.notes,
        organization_id=payload.organization_id,
    )
    return CartItemOut.model_validate(row)


@router.get("/quotes", response_model=list[QuoteOut])
def list_quotes(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> list[QuoteOut]:
    rows = MarketplaceService(db).list_quotes(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )
    return [QuoteOut.model_validate(r) for r in rows]


@router.post("/quotes", response_model=QuoteOut, status_code=201)
def create_quote(
    payload: QuoteCreate,
    session: Session_ = Depends(require_marketplace_manage),
    db: Session = Depends(get_db),
) -> QuoteOut:
    row = MarketplaceService(db).create_quote(
        _actor(session),
        product_id=payload.product_id,
        qty=payload.qty,
        notes=payload.notes,
        organization_id=payload.organization_id,
    )
    return QuoteOut.model_validate(row)


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> list[OrderOut]:
    return MarketplaceService(db).list_orders(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(
    payload: OrderCreate,
    session: Session_ = Depends(require_marketplace_manage),
    db: Session = Depends(get_db),
) -> OrderOut:
    return MarketplaceService(db).create_order(
        _actor(session),
        quote_id=payload.quote_id,
        product_id=payload.product_id,
        qty=payload.qty,
        notes=payload.notes,
        shipping_json=payload.shipping_json,
        organization_id=payload.organization_id,
    )


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: str,
    organization_id: str | None = None,
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> OrderOut:
    return MarketplaceService(db).get_order(_actor(session), order_id, organization_id)


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(
    organization_id: str | None = None,
    seller_id: str | None = None,
    product_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> list[ReviewOut]:
    rows = MarketplaceService(db).list_reviews(
        _actor(session),
        organization_id=organization_id,
        seller_id=seller_id,
        product_id=product_id,
        limit=limit,
        offset=offset,
    )
    return [ReviewOut.model_validate(r) for r in rows]


@router.post("/reviews", response_model=ReviewOut, status_code=201)
def create_review(
    payload: ReviewCreate,
    session: Session_ = Depends(require_marketplace_manage),
    db: Session = Depends(get_db),
) -> ReviewOut:
    row = MarketplaceService(db).create_review(
        _actor(session),
        seller_id=payload.seller_id,
        product_id=payload.product_id,
        rating=payload.rating,
        title=payload.title,
        body=payload.body,
        organization_id=payload.organization_id,
    )
    return ReviewOut.model_validate(row)


@router.get("/favorites", response_model=list[FavoriteOut])
def list_favorites(
    organization_id: str | None = None,
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> list[FavoriteOut]:
    rows = MarketplaceService(db).list_favorites(_actor(session), organization_id=organization_id)
    return [FavoriteOut.model_validate(r) for r in rows]


@router.post("/favorites", response_model=FavoriteOut, status_code=201)
def add_favorite(
    payload: FavoriteCreate,
    session: Session_ = Depends(require_marketplace_manage),
    db: Session = Depends(get_db),
) -> FavoriteOut:
    row = MarketplaceService(db).add_favorite(
        _actor(session),
        product_id=payload.product_id,
        organization_id=payload.organization_id,
    )
    return FavoriteOut.model_validate(row)


@router.get("/saved-searches", response_model=list[SavedSearchOut])
def list_saved_searches(
    organization_id: str | None = None,
    session: Session_ = Depends(require_marketplace_read),
    db: Session = Depends(get_db),
) -> list[SavedSearchOut]:
    rows = MarketplaceService(db).list_saved_searches(
        _actor(session), organization_id=organization_id
    )
    return [SavedSearchOut.model_validate(r) for r in rows]


@router.post("/saved-searches", response_model=SavedSearchOut, status_code=201)
def create_saved_search(
    payload: SavedSearchCreate,
    session: Session_ = Depends(require_marketplace_manage),
    db: Session = Depends(get_db),
) -> SavedSearchOut:
    row = MarketplaceService(db).save_search(
        _actor(session),
        name=payload.name,
        query_json=payload.query_json,
        organization_id=payload.organization_id,
    )
    return SavedSearchOut.model_validate(row)
