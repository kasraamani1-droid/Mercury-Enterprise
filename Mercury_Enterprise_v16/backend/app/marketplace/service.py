"""Program 13 — Mercury Digital Marketplace service.

Platform owns commerce workflows; sellers own inventory. Verification badges and
payment status are architectural readiness only — no regulatory claims, no live PSP.
"""

from __future__ import annotations

import json
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..org.service import OrganizationService
from ..platform.audit_engine import AuditEngine
from ..platform.event_framework import event_framework
from ..shared import ActorContext, clamp_page
from .catalog import CATEGORIES, SELLER_TYPES, VERIFICATION_BADGES
from .models import (
    LISTING_TYPES,
    MarketplaceCartItem,
    MarketplaceFavorite,
    MarketplaceListing,
    MarketplaceOrder,
    MarketplaceOrderLine,
    MarketplaceProduct,
    MarketplaceQuote,
    MarketplaceReview,
    MarketplaceSavedSearch,
    MarketplaceSeller,
)
from .schemas import MarketplaceOverviewOut, OrderLineOut, OrderOut, ProductOut, ProductSearchResponse


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _ai_meta(**kwargs) -> str:
    base = {
        "domain": "marketplace",
        "searchable": True,
        "embedding_ready": False,
        "ai_recommendations_ready": True,
        "ai_ranking_ready": True,
        "ai_alternate_parts_ready": True,
    }
    base.update(kwargs)
    return json.dumps(base)


class MarketplaceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.org = OrganizationService(db)
        self.audit = AuditEngine(db)

    def resolve_org(self, actor: ActorContext, organization_id: str | None = None) -> str:
        org_id = (organization_id or actor.organization_id or "").strip()
        if not org_id:
            raise HTTPException(status_code=400, detail="Organization is required")
        self.org.assert_org_access(
            username=actor.username, session_role=actor.role, organization_id=org_id
        )
        return org_id

    def seed(self, organization_id: str = "org-aviation-east") -> dict[str, int]:
        created = {"listings": 0, "sellers": 0, "products": 0}
        samples = [
            ("parts", "MS21042L3", "Self-locking nut", "Mercury Demo Supply"),
            ("suppliers", "VND-AERO", "Aero Fasteners Inc", "Aero Fasteners Inc"),
            ("tools", "TQ-250", "1/4 drive torque wrench", "Tool Crib East"),
            ("calibration", "CAL-LAB-1", "Primary calibration lab slot", "Metrology East"),
            ("repairs", "REP-AVIONICS", "Avionics shop repair capacity", "Shop AV"),
            ("training", "TRN-B737", "B737 differences course", "Mercury Academy"),
            ("careers", "JOB-TECH-1", "Licensed AME / A&P opening", "HR East"),
            ("publications", "PUB-AMM", "AMM revision catalog entry", "Tech Pubs"),
        ]
        for listing_type, code, title, supplier in samples:
            exists = self.db.scalars(
                select(MarketplaceListing).where(
                    MarketplaceListing.organization_id == organization_id,
                    MarketplaceListing.listing_type == listing_type,
                    MarketplaceListing.code == code,
                    MarketplaceListing.deleted_at.is_(None),
                )
            ).first()
            if exists:
                continue
            self.db.add(
                MarketplaceListing(
                    organization_id=organization_id,
                    listing_type=listing_type,
                    code=code,
                    title=title,
                    summary=f"Readiness listing for {listing_type}",
                    supplier_name=supplier,
                    status="published",
                    ai_metadata_json=_ai_meta(listing_type=listing_type),
                    created_by="system",
                )
            )
            created["listings"] += 1

        seller_samples = [
            (
                "parts_supplier",
                "Aero Fasteners Inc",
                "Aero Fasteners",
                ["oem"],
                ["hardware", "fasteners"],
            ),
            (
                "repair_station",
                "Shop AV Avionics LLC",
                "Shop AV",
                ["repair_station", "amo"],
                ["avionics", "component_repairs"],
            ),
            (
                "calibration_laboratory",
                "Metrology East Lab",
                "Metrology East",
                ["calibration_accreditation"],
                ["torque", "pressure", "electrical"],
            ),
            (
                "training_organization",
                "Mercury Academy East",
                "Mercury Academy",
                ["training_approval"],
                ["type_courses", "ewis", "human_factors"],
            ),
            (
                "tool_manufacturer",
                "Tool Crib East Manufacturing",
                "Tool Crib East",
                [],
                ["special_tools", "gse"],
            ),
        ]
        sellers_by_type: dict[str, MarketplaceSeller] = {}
        for seller_type, legal, display, badges, caps in seller_samples:
            row = self.db.scalars(
                select(MarketplaceSeller).where(
                    MarketplaceSeller.organization_id == organization_id,
                    MarketplaceSeller.seller_type == seller_type,
                    MarketplaceSeller.legal_name == legal,
                    MarketplaceSeller.deleted_at.is_(None),
                )
            ).first()
            if row is None:
                row = MarketplaceSeller(
                    organization_id=organization_id,
                    seller_type=seller_type,
                    legal_name=legal,
                    display_name=display,
                    summary=f"Demo seller profile ({seller_type})",
                    contact_email=f"sales@{display.lower().replace(' ', '')}.example",
                    locations_json=json.dumps([{"city": "Toronto", "country": "CA"}]),
                    capabilities_json=json.dumps(caps),
                    certificates_json=json.dumps([]),
                    approvals_json=json.dumps([]),
                    verification_badges_json=json.dumps(
                        [b for b in badges if b in VERIFICATION_BADGES]
                    ),
                    avg_turnaround_days=7 if "repair" in seller_type else 3,
                    status="active",
                    ai_metadata_json=_ai_meta(entity="seller", seller_type=seller_type),
                    created_by="system",
                )
                self.db.add(row)
                self.db.flush()
                created["sellers"] += 1
            sellers_by_type[seller_type] = row

        product_samples = [
            (
                "parts_supplier",
                "aircraft_parts",
                "MS21042L3",
                "Self-locking nut MS21042L3",
                "sale",
                Decimal("1.2500"),
                500,
                "in_stock",
            ),
            (
                "parts_supplier",
                "consumables",
                "CONS-LOCTITE-242",
                "Threadlocker 242 (aviation grade)",
                "sale",
                Decimal("18.5000"),
                120,
                "in_stock",
            ),
            (
                "tool_manufacturer",
                "special_tools",
                "TQ-250",
                "1/4 drive torque wrench",
                "sale",
                Decimal("420.0000"),
                8,
                "in_stock",
            ),
            (
                "tool_manufacturer",
                "special_tools",
                "TQ-250-RENT",
                "Torque wrench rental (7 day)",
                "rental",
                Decimal("45.0000"),
                4,
                "in_stock",
            ),
            (
                "calibration_laboratory",
                "calibration",
                "CAL-TQ-STD",
                "Torque tool calibration service",
                "service",
                Decimal("95.0000"),
                50,
                "available",
            ),
            (
                "repair_station",
                "avionics_repairs",
                "REP-TCAS-UNIT",
                "TCAS computer repair",
                "service",
                Decimal("4500.0000"),
                5,
                "quote_required",
            ),
            (
                "training_organization",
                "training",
                "TRN-B737-DIFF",
                "B737 differences course",
                "training",
                Decimal("2800.0000"),
                20,
                "scheduled",
            ),
            (
                "training_organization",
                "jobs",
                "JOB-AME-EAST-1",
                "Licensed AME / A&P — East Base",
                "job",
                Decimal("0"),
                1,
                "open",
            ),
        ]
        for stype, category, sku, title, mode, price, qty, avail in product_samples:
            seller = sellers_by_type.get(stype)
            if seller is None:
                continue
            exists = self.db.scalars(
                select(MarketplaceProduct).where(
                    MarketplaceProduct.organization_id == organization_id,
                    MarketplaceProduct.sku == sku,
                    MarketplaceProduct.deleted_at.is_(None),
                )
            ).first()
            if exists:
                continue
            self.db.add(
                MarketplaceProduct(
                    organization_id=organization_id,
                    seller_id=seller.id,
                    category=category,
                    sku=sku,
                    title=title,
                    summary=f"Demo catalog offer — {category}",
                    description=title,
                    offer_mode=mode,
                    currency="USD",
                    unit_price=price,
                    qty_available=qty,
                    availability=avail,
                    serial_tracked=_bool_str(False),
                    batch_tracked=_bool_str(category in {"consumables", "expendables"}),
                    certificates_json=json.dumps(
                        [{"type": "8130", "status": "architecture_ready"}]
                        if category == "aircraft_parts"
                        else []
                    ),
                    warranty_json=json.dumps({"months": 12} if mode == "sale" else {}),
                    compatibility_json=json.dumps(
                        {"aircraft": [], "engines": [], "components": []}
                    ),
                    supersessions_json="[]",
                    alternates_json="[]",
                    publications_json="[]",
                    turnaround_days=14 if mode == "service" else 0,
                    status="published",
                    ai_metadata_json=_ai_meta(
                        entity="product",
                        category=category,
                        offer_mode=mode,
                        alternate_parts_ready=True,
                    ),
                    created_by="system",
                )
            )
            created["products"] += 1

        if any(created.values()):
            self.db.commit()
        return created

    def overview(
        self, actor: ActorContext, organization_id: str | None = None
    ) -> MarketplaceOverviewOut:
        org_id = self.resolve_org(actor, organization_id)
        listings = int(
            self.db.scalar(
                select(func.count())
                .select_from(MarketplaceListing)
                .where(
                    MarketplaceListing.organization_id == org_id,
                    MarketplaceListing.deleted_at.is_(None),
                )
            )
            or 0
        )
        sellers = int(
            self.db.scalar(
                select(func.count())
                .select_from(MarketplaceSeller)
                .where(
                    MarketplaceSeller.organization_id == org_id,
                    MarketplaceSeller.deleted_at.is_(None),
                )
            )
            or 0
        )
        products = int(
            self.db.scalar(
                select(func.count())
                .select_from(MarketplaceProduct)
                .where(
                    MarketplaceProduct.organization_id == org_id,
                    MarketplaceProduct.deleted_at.is_(None),
                )
            )
            or 0
        )
        quotes = int(
            self.db.scalar(
                select(func.count())
                .select_from(MarketplaceQuote)
                .where(MarketplaceQuote.organization_id == org_id)
            )
            or 0
        )
        orders = int(
            self.db.scalar(
                select(func.count())
                .select_from(MarketplaceOrder)
                .where(
                    MarketplaceOrder.organization_id == org_id,
                    MarketplaceOrder.deleted_at.is_(None),
                )
            )
            or 0
        )
        reviews = int(
            self.db.scalar(
                select(func.count())
                .select_from(MarketplaceReview)
                .where(MarketplaceReview.organization_id == org_id)
            )
            or 0
        )
        return MarketplaceOverviewOut(
            organization_id=org_id,
            listings=listings,
            sellers=sellers,
            products=products,
            quotes=quotes,
            orders=orders,
            reviews=reviews,
            categories=len(CATEGORIES),
        )

    def categories(self) -> list[dict[str, str]]:
        return [{"code": c, "name": n, "family": f} for c, n, f in CATEGORIES]

    def create(
        self,
        actor: ActorContext,
        *,
        listing_type: str,
        code: str,
        title: str,
        summary: str = "",
        supplier_name: str = "",
        organization_id: str | None = None,
    ) -> MarketplaceListing:
        if listing_type not in LISTING_TYPES:
            raise HTTPException(status_code=400, detail="Invalid listing_type")
        org_id = self.resolve_org(actor, organization_id)
        row = MarketplaceListing(
            organization_id=org_id,
            listing_type=listing_type,
            code=code.strip().upper(),
            title=title.strip(),
            summary=summary.strip(),
            supplier_name=supplier_name.strip(),
            status="draft",
            ai_metadata_json=_ai_meta(listing_type=listing_type),
            created_by=actor.username,
        )
        self.db.add(row)
        try:
            self.db.flush()
            self.audit.require(
                actor,
                action="marketplace.listing.create",
                target_type="marketplace_listing",
                target_id=row.id,
                organization_id=org_id,
                details=row.code,
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Listing already exists") from exc
        event_framework.publish_sync(
            "marketplace.listing.created",
            {"id": row.id, "listing_type": listing_type, "code": row.code},
            organization_id=org_id,
            source="marketplace",
        )
        return row

    def list(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        listing_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MarketplaceListing]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(MarketplaceListing).where(
            MarketplaceListing.organization_id == org_id,
            MarketplaceListing.deleted_at.is_(None),
        )
        if listing_type:
            stmt = stmt.where(MarketplaceListing.listing_type == listing_type)
        return list(
            self.db.scalars(
                stmt.order_by(MarketplaceListing.listing_type, MarketplaceListing.code)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def create_seller(
        self,
        actor: ActorContext,
        *,
        seller_type: str,
        legal_name: str,
        display_name: str = "",
        summary: str = "",
        contact_email: str = "",
        contact_phone: str = "",
        locations_json: str = "[]",
        capabilities_json: str = "[]",
        certificates_json: str = "[]",
        approvals_json: str = "[]",
        verification_badges_json: str = "[]",
        organization_id: str | None = None,
    ) -> MarketplaceSeller:
        if seller_type not in SELLER_TYPES:
            raise HTTPException(status_code=400, detail="Invalid seller_type")
        org_id = self.resolve_org(actor, organization_id)
        try:
            badges = json.loads(verification_badges_json or "[]")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid verification_badges_json") from exc
        if not isinstance(badges, list):
            raise HTTPException(status_code=400, detail="verification_badges_json must be a list")
        bad = [b for b in badges if b not in VERIFICATION_BADGES]
        if bad:
            raise HTTPException(status_code=400, detail=f"Unknown verification badges: {bad}")
        row = MarketplaceSeller(
            organization_id=org_id,
            seller_type=seller_type,
            legal_name=legal_name.strip(),
            display_name=(display_name or legal_name).strip(),
            summary=summary.strip(),
            contact_email=contact_email.strip(),
            contact_phone=contact_phone.strip(),
            locations_json=locations_json,
            capabilities_json=capabilities_json,
            certificates_json=certificates_json,
            approvals_json=approvals_json,
            verification_badges_json=json.dumps(badges),
            status="active",
            ai_metadata_json=_ai_meta(entity="seller", seller_type=seller_type),
            created_by=actor.username,
        )
        self.db.add(row)
        self.db.flush()
        self.audit.require(
            actor,
            action="marketplace.seller.create",
            target_type="marketplace_seller",
            target_id=row.id,
            organization_id=org_id,
            details=row.legal_name,
        )
        self.db.commit()
        event_framework.publish_sync(
            "marketplace.seller.created",
            {"id": row.id, "seller_type": seller_type},
            organization_id=org_id,
            source="marketplace",
        )
        return row

    def list_sellers(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        seller_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MarketplaceSeller]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(MarketplaceSeller).where(
            MarketplaceSeller.organization_id == org_id,
            MarketplaceSeller.deleted_at.is_(None),
        )
        if seller_type:
            stmt = stmt.where(MarketplaceSeller.seller_type == seller_type)
        return list(
            self.db.scalars(
                stmt.order_by(MarketplaceSeller.seller_type, MarketplaceSeller.legal_name)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def get_seller(
        self, actor: ActorContext, seller_id: str, organization_id: str | None = None
    ) -> MarketplaceSeller:
        org_id = self.resolve_org(actor, organization_id)
        row = self.db.get(MarketplaceSeller, seller_id)
        if row is None or row.deleted_at is not None or row.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Seller not found")
        return row

    def _get_seller_row(self, org_id: str, seller_id: str) -> MarketplaceSeller:
        seller = self.db.get(MarketplaceSeller, seller_id)
        if seller is None or seller.deleted_at is not None or seller.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Seller not found")
        return seller

    def create_product(
        self,
        actor: ActorContext,
        *,
        seller_id: str,
        category: str,
        sku: str,
        title: str,
        summary: str = "",
        description: str = "",
        offer_mode: str = "sale",
        currency: str = "USD",
        unit_price: Decimal = Decimal("0"),
        qty_available: int = 0,
        availability: str = "in_stock",
        serial_tracked: bool = False,
        batch_tracked: bool = False,
        images_json: str = "[]",
        documents_json: str = "[]",
        certificates_json: str = "[]",
        warranty_json: str = "{}",
        compatibility_json: str = "{}",
        supersessions_json: str = "[]",
        alternates_json: str = "[]",
        publications_json: str = "[]",
        turnaround_days: int = 0,
        status: str = "published",
        organization_id: str | None = None,
    ) -> MarketplaceProduct:
        cat_codes = {c[0] for c in CATEGORIES}
        if category not in cat_codes:
            raise HTTPException(status_code=400, detail="Invalid category")
        org_id = self.resolve_org(actor, organization_id)
        self._get_seller_row(org_id, seller_id)
        row = MarketplaceProduct(
            organization_id=org_id,
            seller_id=seller_id,
            category=category,
            sku=sku.strip().upper(),
            title=title.strip(),
            summary=summary.strip(),
            description=description.strip(),
            offer_mode=offer_mode,
            currency=currency.strip().upper() or "USD",
            unit_price=unit_price,
            qty_available=qty_available,
            availability=availability,
            serial_tracked=_bool_str(serial_tracked),
            batch_tracked=_bool_str(batch_tracked),
            images_json=images_json,
            documents_json=documents_json,
            certificates_json=certificates_json,
            warranty_json=warranty_json,
            compatibility_json=compatibility_json,
            supersessions_json=supersessions_json,
            alternates_json=alternates_json,
            publications_json=publications_json,
            turnaround_days=turnaround_days,
            status=status,
            ai_metadata_json=_ai_meta(entity="product", category=category, offer_mode=offer_mode),
            created_by=actor.username,
        )
        self.db.add(row)
        self.db.flush()
        self.audit.require(
            actor,
            action="marketplace.product.create",
            target_type="marketplace_product",
            target_id=row.id,
            organization_id=org_id,
            details=row.sku,
        )
        self.db.commit()
        event_framework.publish_sync(
            "marketplace.product.created",
            {"id": row.id, "sku": row.sku, "category": category},
            organization_id=org_id,
            source="marketplace",
        )
        return row

    def list_products(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        category: str | None = None,
        seller_id: str | None = None,
        offer_mode: str | None = None,
        status: str | None = "published",
        limit: int = 100,
        offset: int = 0,
    ) -> list[MarketplaceProduct]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(MarketplaceProduct).where(
            MarketplaceProduct.organization_id == org_id,
            MarketplaceProduct.deleted_at.is_(None),
        )
        if category:
            stmt = stmt.where(MarketplaceProduct.category == category)
        if seller_id:
            stmt = stmt.where(MarketplaceProduct.seller_id == seller_id)
        if offer_mode:
            stmt = stmt.where(MarketplaceProduct.offer_mode == offer_mode)
        if status:
            stmt = stmt.where(MarketplaceProduct.status == status)
        return list(
            self.db.scalars(
                stmt.order_by(MarketplaceProduct.category, MarketplaceProduct.sku)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def get_product(
        self, actor: ActorContext, product_id: str, organization_id: str | None = None
    ) -> MarketplaceProduct:
        org_id = self.resolve_org(actor, organization_id)
        row = self.db.get(MarketplaceProduct, product_id)
        if row is None or row.deleted_at is not None or row.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Product not found")
        return row

    def search_products(
        self,
        actor: ActorContext,
        *,
        q: str = "",
        category: str | None = None,
        organization_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ProductSearchResponse:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(MarketplaceProduct).where(
            MarketplaceProduct.organization_id == org_id,
            MarketplaceProduct.deleted_at.is_(None),
            MarketplaceProduct.status == "published",
        )
        if category:
            stmt = stmt.where(MarketplaceProduct.category == category)
        query = (q or "").strip()
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    MarketplaceProduct.sku.ilike(like),
                    MarketplaceProduct.title.ilike(like),
                    MarketplaceProduct.summary.ilike(like),
                    MarketplaceProduct.category.ilike(like),
                )
            )
        rows = list(
            self.db.scalars(stmt.order_by(MarketplaceProduct.title).limit(lim).offset(off)).all()
        )
        return ProductSearchResponse(
            query=query,
            total=len(rows),
            items=[ProductOut.model_validate(r) for r in rows],
        )

    def add_cart_item(
        self,
        actor: ActorContext,
        *,
        product_id: str,
        qty: int = 1,
        notes: str = "",
        organization_id: str | None = None,
    ) -> MarketplaceCartItem:
        org_id = self.resolve_org(actor, organization_id)
        product = self.get_product(actor, product_id, org_id)
        existing = self.db.scalars(
            select(MarketplaceCartItem).where(
                MarketplaceCartItem.organization_id == org_id,
                MarketplaceCartItem.username == actor.username,
                MarketplaceCartItem.product_id == product.id,
            )
        ).first()
        if existing:
            existing.qty = qty
            existing.notes = notes
            self.db.commit()
            return existing
        row = MarketplaceCartItem(
            organization_id=org_id,
            username=actor.username,
            product_id=product.id,
            qty=qty,
            notes=notes,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def list_cart(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
    ) -> list[MarketplaceCartItem]:
        org_id = self.resolve_org(actor, organization_id)
        return list(
            self.db.scalars(
                select(MarketplaceCartItem).where(
                    MarketplaceCartItem.organization_id == org_id,
                    MarketplaceCartItem.username == actor.username,
                )
            ).all()
        )

    def create_quote(
        self,
        actor: ActorContext,
        *,
        product_id: str,
        qty: int = 1,
        notes: str = "",
        organization_id: str | None = None,
    ) -> MarketplaceQuote:
        org_id = self.resolve_org(actor, organization_id)
        product = self.get_product(actor, product_id, org_id)
        seller = self.db.get(MarketplaceSeller, product.seller_id)
        seller_org = seller.organization_id if seller else product.organization_id
        count = int(
            self.db.scalar(
                select(func.count())
                .select_from(MarketplaceQuote)
                .where(MarketplaceQuote.organization_id == org_id)
            )
            or 0
        )
        row = MarketplaceQuote(
            organization_id=org_id,
            seller_organization_id=seller_org,
            quote_number=f"QT-{org_id[-4:].upper()}-{count + 1:05d}",
            product_id=product.id,
            qty=qty,
            unit_price=product.unit_price,
            currency=product.currency,
            status="sent",
            notes=notes,
            created_by=actor.username,
        )
        self.db.add(row)
        self.db.flush()
        self.audit.require(
            actor,
            action="marketplace.quote.create",
            target_type="marketplace_quote",
            target_id=row.id,
            organization_id=org_id,
            details=row.quote_number,
        )
        self.db.commit()
        event_framework.publish_sync(
            "marketplace.quote.created",
            {"id": row.id, "quote_number": row.quote_number, "product_id": product.id},
            organization_id=org_id,
            source="marketplace",
        )
        return row

    def list_quotes(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MarketplaceQuote]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        return list(
            self.db.scalars(
                select(MarketplaceQuote)
                .where(MarketplaceQuote.organization_id == org_id)
                .order_by(MarketplaceQuote.created_at.desc())
                .limit(lim)
                .offset(off)
            ).all()
        )

    def _order_out(self, order: MarketplaceOrder) -> OrderOut:
        lines = list(
            self.db.scalars(
                select(MarketplaceOrderLine).where(MarketplaceOrderLine.order_id == order.id)
            ).all()
        )
        data = OrderOut.model_validate(order)
        data.lines = [OrderLineOut.model_validate(ln) for ln in lines]
        return data

    def create_order(
        self,
        actor: ActorContext,
        *,
        quote_id: str | None = None,
        product_id: str | None = None,
        qty: int = 1,
        notes: str = "",
        shipping_json: str = "{}",
        organization_id: str | None = None,
    ) -> OrderOut:
        org_id = self.resolve_org(actor, organization_id)
        product: MarketplaceProduct | None = None
        quote: MarketplaceQuote | None = None
        if quote_id:
            quote = self.db.get(MarketplaceQuote, quote_id)
            if quote is None or quote.organization_id != org_id:
                raise HTTPException(status_code=404, detail="Quote not found")
            product = self.get_product(actor, quote.product_id, org_id)
            qty = quote.qty
        elif product_id:
            product = self.get_product(actor, product_id, org_id)
        else:
            raise HTTPException(status_code=400, detail="quote_id or product_id required")

        seller = self.db.get(MarketplaceSeller, product.seller_id)
        seller_org = seller.organization_id if seller else product.organization_id
        unit = quote.unit_price if quote else product.unit_price
        line_total = (unit * Decimal(qty)).quantize(Decimal("0.0001"))
        count = int(
            self.db.scalar(
                select(func.count())
                .select_from(MarketplaceOrder)
                .where(MarketplaceOrder.organization_id == org_id)
            )
            or 0
        )
        order = MarketplaceOrder(
            organization_id=org_id,
            seller_organization_id=seller_org,
            order_number=f"PO-{org_id[-4:].upper()}-{count + 1:05d}",
            quote_id=quote.id if quote else "",
            status="submitted",
            currency=product.currency,
            total_amount=line_total,
            shipping_json=shipping_json,
            invoice_ref="",
            payment_status="not_configured",
            notes=notes,
            created_by=actor.username,
        )
        self.db.add(order)
        self.db.flush()
        self.db.add(
            MarketplaceOrderLine(
                organization_id=org_id,
                order_id=order.id,
                product_id=product.id,
                sku=product.sku,
                title=product.title,
                qty=qty,
                unit_price=unit,
                line_total=line_total,
            )
        )
        if quote:
            quote.status = "accepted"
        self.audit.require(
            actor,
            action="marketplace.order.create",
            target_type="marketplace_order",
            target_id=order.id,
            organization_id=org_id,
            details=order.order_number,
        )
        self.db.commit()
        event_framework.publish_sync(
            "marketplace.order.created",
            {"id": order.id, "order_number": order.order_number, "total": str(line_total)},
            organization_id=org_id,
            source="marketplace",
        )
        return self._order_out(order)

    def list_orders(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OrderOut]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        rows = list(
            self.db.scalars(
                select(MarketplaceOrder)
                .where(
                    MarketplaceOrder.organization_id == org_id,
                    MarketplaceOrder.deleted_at.is_(None),
                )
                .order_by(MarketplaceOrder.created_at.desc())
                .limit(lim)
                .offset(off)
            ).all()
        )
        return [self._order_out(r) for r in rows]

    def get_order(
        self, actor: ActorContext, order_id: str, organization_id: str | None = None
    ) -> OrderOut:
        org_id = self.resolve_org(actor, organization_id)
        row = self.db.get(MarketplaceOrder, order_id)
        if row is None or row.deleted_at is not None or row.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Order not found")
        return self._order_out(row)

    def create_review(
        self,
        actor: ActorContext,
        *,
        seller_id: str = "",
        product_id: str = "",
        rating: int = 5,
        title: str = "",
        body: str = "",
        organization_id: str | None = None,
    ) -> MarketplaceReview:
        if not seller_id and not product_id:
            raise HTTPException(status_code=400, detail="seller_id or product_id required")
        org_id = self.resolve_org(actor, organization_id)
        if product_id:
            product = self.get_product(actor, product_id, org_id)
            if not seller_id:
                seller_id = product.seller_id
        if seller_id:
            self.get_seller(actor, seller_id, org_id)
        row = MarketplaceReview(
            organization_id=org_id,
            seller_id=seller_id or "",
            product_id=product_id or "",
            rating=rating,
            title=title.strip(),
            body=body.strip(),
            created_by=actor.username,
            status="published",
        )
        self.db.add(row)
        self.db.flush()
        if seller_id:
            self._recompute_seller_rating(seller_id)
        self.audit.require(
            actor,
            action="marketplace.review.create",
            target_type="marketplace_review",
            target_id=row.id,
            organization_id=org_id,
            details=str(rating),
        )
        self.db.commit()
        return row

    def _recompute_seller_rating(self, seller_id: str) -> None:
        rows = list(
            self.db.scalars(
                select(MarketplaceReview).where(
                    MarketplaceReview.seller_id == seller_id,
                    MarketplaceReview.status == "published",
                )
            ).all()
        )
        seller = self.db.get(MarketplaceSeller, seller_id)
        if seller is None:
            return
        if not rows:
            seller.rating_avg = "0"
            seller.review_count = 0
            return
        avg = sum(r.rating for r in rows) / len(rows)
        seller.rating_avg = f"{avg:.2f}"
        seller.review_count = len(rows)

    def list_reviews(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        seller_id: str | None = None,
        product_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MarketplaceReview]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(MarketplaceReview).where(MarketplaceReview.organization_id == org_id)
        if seller_id:
            stmt = stmt.where(MarketplaceReview.seller_id == seller_id)
        if product_id:
            stmt = stmt.where(MarketplaceReview.product_id == product_id)
        return list(
            self.db.scalars(
                stmt.order_by(MarketplaceReview.created_at.desc()).limit(lim).offset(off)
            ).all()
        )

    def add_favorite(
        self,
        actor: ActorContext,
        *,
        product_id: str,
        organization_id: str | None = None,
    ) -> MarketplaceFavorite:
        org_id = self.resolve_org(actor, organization_id)
        product = self.get_product(actor, product_id, org_id)
        existing = self.db.scalars(
            select(MarketplaceFavorite).where(
                MarketplaceFavorite.organization_id == org_id,
                MarketplaceFavorite.username == actor.username,
                MarketplaceFavorite.product_id == product.id,
            )
        ).first()
        if existing:
            return existing
        row = MarketplaceFavorite(
            organization_id=org_id,
            username=actor.username,
            product_id=product.id,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def list_favorites(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
    ) -> list[MarketplaceFavorite]:
        org_id = self.resolve_org(actor, organization_id)
        return list(
            self.db.scalars(
                select(MarketplaceFavorite).where(
                    MarketplaceFavorite.organization_id == org_id,
                    MarketplaceFavorite.username == actor.username,
                )
            ).all()
        )

    def save_search(
        self,
        actor: ActorContext,
        *,
        name: str,
        query_json: str = "{}",
        organization_id: str | None = None,
    ) -> MarketplaceSavedSearch:
        org_id = self.resolve_org(actor, organization_id)
        row = MarketplaceSavedSearch(
            organization_id=org_id,
            username=actor.username,
            name=name.strip(),
            query_json=query_json,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def list_saved_searches(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
    ) -> list[MarketplaceSavedSearch]:
        org_id = self.resolve_org(actor, organization_id)
        return list(
            self.db.scalars(
                select(MarketplaceSavedSearch).where(
                    MarketplaceSavedSearch.organization_id == org_id,
                    MarketplaceSavedSearch.username == actor.username,
                )
            ).all()
        )
