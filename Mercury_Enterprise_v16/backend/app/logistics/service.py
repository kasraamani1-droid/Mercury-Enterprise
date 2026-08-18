"""Program B – Enterprise Logistics service.

Warehouse hierarchy, part master, stock ledger (FIFO/FEFO), tools & calibration,
material requests, vendors, the purchase-request → RFQ → PO → receipt → putaway
chain, shipments, scanning, dashboard KPIs and planning integration.

Every mutation is organization-scoped and audited; critical stock and approval
operations abort (HTTP 500) when the audit trail cannot be written.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..org.service import OrganizationService
from .models import (
    Aisle,
    Bin,
    Building,
    Location,
    LostToolReport,
    MaterialRequest,
    MaterialRequestLine,
    PartAttachment,
    PartFamily,
    PartFamilyMember,
    PartIdentifier,
    PartMaster,
    PartSupersession,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequest,
    PurchaseRequestLine,
    Receipt,
    ReceiptLine,
    Rfq,
    RfqQuote,
    Room,
    RotableCycle,
    Shelf,
    Shipment,
    StockBalance,
    StockMovement,
    StockReservation,
    StockUnit,
    StoreArea,
    Tool,
    ToolCalibration,
    ToolHistory,
    ToolIssue,
    ToolReservation,
    Vendor,
    VendorInvoice,
    Warehouse,
    WarehouseTransfer,
    WarehouseTransferLine,
    Zone,
)
from .repository import LogisticsRepository
from .schemas import (
    AdjustStockRequest,
    AttachmentCreate,
    AttachmentOut,
    BulkAdjustRequest,
    BulkAdjustResult,
    BulkAdjustResultLine,
    DashboardOut,
    FamilyCreate,
    FamilyMemberOut,
    FamilyOut,
    IdentifierCreate,
    IdentifierOut,
    IssueStockRequest,
    LocationCreate,
    LocationOut,
    LostToolReportCreate,
    LostToolReportOut,
    MaterialPlanningLineResult,
    MaterialPlanningResult,
    MaterialRequestCreate,
    MaterialRequestDetailOut,
    MaterialRequestIssueRequest,
    MaterialRequestLineOut,
    MaterialRequestOut,
    MaterialRequestReturnRequest,
    PartMasterCreate,
    PartMasterOut,
    PartMasterUpdate,
    PurchaseOrderCreateFromRfq,
    PurchaseOrderDetailOut,
    PurchaseOrderLineOut,
    PurchaseOrderOut,
    PurchaseRequestCreate,
    PurchaseRequestDetailOut,
    PurchaseRequestLineOut,
    PurchaseRequestOut,
    ReceiptCreate,
    ReceiptDetailOut,
    ReceiptInspectRequest,
    ReceiptLineOut,
    ReceiptOut,
    ReceiptPutawayRequest,
    ReceiveStockRequest,
    ReservationCreate,
    ReservationOut,
    RfqDetailOut,
    RfqOut,
    RfqQuoteCreate,
    RfqQuoteOut,
    RotableCycleCloseRequest,
    RotableCycleCreate,
    RotableCycleOut,
    ScanOut,
    ScanRequest,
    ScrapStockRequest,
    SeedDemoOut,
    ShipmentCreate,
    ShipmentOut,
    ShortageItemOut,
    ShortagesOut,
    StockBalanceDetailOut,
    StockMovementOut,
    StockUnitOut,
    SupersessionCreate,
    SupersessionOut,
    ToolCalibrateRequest,
    ToolCalibrationOut,
    ToolCreate,
    ToolHistoryOut,
    ToolIssueOut,
    ToolIssueRequest,
    ToolOut,
    ToolPlanningLineResult,
    ToolPlanningResult,
    ToolReservationOut,
    ToolReserveRequest,
    ToolUpdate,
    TransferCompleteRequest,
    TransferCreate,
    TransferDetailOut,
    TransferLineOut,
    TransferOut,
    VendorCreate,
    VendorInvoiceCreate,
    VendorInvoiceOut,
    VendorOut,
    VendorUpdate,
    WarehouseCreate,
    WarehouseOut,
    WarehouseTreeCreate,
    WarehouseTreeOut,
)

logger = logging.getLogger("mercury.logistics")

ZERO = Decimal("0")

MATERIAL_REQUEST_TRANSITIONS: dict[str, frozenset[str]] = {
    "requested": frozenset({"approved", "cancelled"}),
    "approved": frozenset({"reserved", "issued", "cancelled"}),
    "reserved": frozenset({"issued", "cancelled"}),
    "issued": frozenset({"returned"}),
    "returned": frozenset(),
    "cancelled": frozenset(),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _truthy(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in {"1", "true", "yes", "on"}


def _dec(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return ZERO
    return Decimal(str(value))


def _number(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


@dataclass(frozen=True)
class ActorContext:
    """Session-derived identity used for org scoping and audit."""

    username: str
    role: str
    organization_id: str
    site_id: str = ""


class LogisticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = LogisticsRepository(db)
        self.org = OrganizationService(db)

    # ------------------------------------------------------------------
    # Transaction / audit helpers
    # ------------------------------------------------------------------
    def _commit_or_conflict(self, *, detail: str) -> None:
        try:
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail=detail) from exc

    def _audit_required(
        self,
        actor: ActorContext | None,
        *,
        action: str,
        target_type: str,
        target_id: str,
        organization_id: str | None = None,
        details: str = "",
    ) -> None:
        """Audit critical operations. A failed audit rolls the operation back."""
        if actor is None:
            return
        try:
            record_audit(
                self.db,
                action=action,
                actor=actor.username,
                actor_role=actor.role,
                organization_id=organization_id or actor.organization_id,
                site_id=actor.site_id,
                target_type=target_type,
                target_id=target_id,
                source="api",
                outcome="success",
                origin="operator",
                details=details,
            )
            self.repo.flush()
        except Exception as exc:
            self.repo.rollback()
            logger.exception("logistics audit failed action=%s target=%s", action, target_id)
            raise HTTPException(
                status_code=500, detail="Audit trail write failed; operation rolled back"
            ) from exc

    # ------------------------------------------------------------------
    # Organization scoping
    # ------------------------------------------------------------------
    def resolve_org_id(self, actor: ActorContext, requested_org_id: str | None = None) -> str:
        org_id = (requested_org_id or actor.organization_id or "").strip()
        if not org_id:
            raise HTTPException(status_code=400, detail="Organization is required")
        self.org.assert_org_access(username=actor.username, session_role=actor.role, organization_id=org_id)
        return org_id

    # ------------------------------------------------------------------
    # Lookup helpers (all org-scoped, 404 on miss)
    # ------------------------------------------------------------------
    def _require_part(self, org_id: str, part_id: str, *, for_update: bool = False) -> PartMaster:
        row = self.repo.get_part(org_id, part_id, for_update=for_update)
        if row is None:
            raise HTTPException(status_code=404, detail="Part not found")
        return row

    def _require_location(self, org_id: str, location_id: str) -> Location:
        row = self.repo.get_location(org_id, location_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Location not found")
        return row

    def _require_warehouse(self, org_id: str, warehouse_id: str) -> Warehouse:
        row = self.repo.get_warehouse(org_id, warehouse_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        return row

    def _require_tool(self, org_id: str, tool_id: str, *, for_update: bool = False) -> Tool:
        row = self.repo.get_tool(org_id, tool_id, for_update=for_update)
        if row is None:
            raise HTTPException(status_code=404, detail="Tool not found")
        return row

    def _require_vendor(self, org_id: str, vendor_id: str) -> Vendor:
        row = self.repo.get_vendor(org_id, vendor_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return row

    def _require_stock_unit(self, org_id: str, unit_id: str, *, for_update: bool = False) -> StockUnit:
        row = self.repo.get_stock_unit(org_id, unit_id, for_update=for_update)
        if row is None:
            raise HTTPException(status_code=404, detail="Stock unit not found")
        return row

    # ------------------------------------------------------------------
    # Warehouses & locations
    # ------------------------------------------------------------------
    def create_warehouse(self, payload: WarehouseCreate, actor: ActorContext) -> WarehouseOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        code = payload.code.strip().upper()
        if self.repo.get_warehouse_by_code(org_id, code) is not None:
            raise HTTPException(status_code=409, detail="Warehouse code already exists")
        now = _utcnow()
        row = Warehouse(
            organization_id=org_id,
            code=code,
            name=payload.name.strip(),
            warehouse_type=payload.warehouse_type,
            is_virtual=_flag(payload.is_virtual or payload.warehouse_type == "virtual"),
            is_bonded=_flag(payload.is_bonded or payload.warehouse_type == "bonded"),
            address=(payload.address or "").strip(),
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_warehouse(row)
        self._audit_required(
            actor,
            action="logistics.warehouse.create",
            target_type="logistics_warehouse",
            target_id=row.id,
            organization_id=org_id,
            details=f"code={code}",
        )
        self._commit_or_conflict(detail="Warehouse conflict")
        self.repo.refresh(row)
        return WarehouseOut.model_validate(row)

    def list_warehouses(
        self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[WarehouseOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            WarehouseOut.model_validate(r)
            for r in self.repo.list_warehouses(organization_id=org_id, limit=limit, offset=offset)
        ]

    def create_warehouse_tree(self, payload: WarehouseTreeCreate, actor: ActorContext) -> WarehouseTreeOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        code = payload.code.strip().upper()
        if self.repo.get_warehouse_by_code(org_id, code) is not None:
            raise HTTPException(status_code=409, detail="Warehouse code already exists")
        warehouse, locations = self._build_warehouse_tree(
            org_id,
            code=code,
            name=payload.name.strip(),
            warehouse_type=payload.warehouse_type,
            is_bonded=payload.is_bonded,
            address=(payload.address or "").strip(),
            building_code=payload.building_code.strip().upper() or "BLD-1",
            store_code=payload.store_code.strip().upper() or "ST-1",
            room_code=payload.room_code.strip().upper() or "RM-1",
            zone_types=payload.zone_types or ["general"],
            bins_per_zone=payload.bins_per_zone,
        )
        self._audit_required(
            actor,
            action="logistics.warehouse.tree.create",
            target_type="logistics_warehouse",
            target_id=warehouse.id,
            organization_id=org_id,
            details=f"code={code};locations={len(locations)}",
        )
        self._commit_or_conflict(detail="Warehouse tree conflict")
        self.repo.refresh(warehouse)
        return WarehouseTreeOut(
            warehouse=WarehouseOut.model_validate(warehouse),
            locations=[LocationOut.model_validate(loc) for loc in locations],
        )

    def _build_warehouse_tree(
        self,
        org_id: str,
        *,
        code: str,
        name: str,
        warehouse_type: str,
        is_bonded: bool,
        address: str,
        building_code: str,
        store_code: str,
        room_code: str,
        zone_types: list[str],
        bins_per_zone: int,
    ) -> tuple[Warehouse, list[Location]]:
        now = _utcnow()
        warehouse = Warehouse(
            organization_id=org_id,
            code=code,
            name=name,
            warehouse_type=warehouse_type,
            is_virtual=_flag(warehouse_type == "virtual"),
            is_bonded=_flag(is_bonded or warehouse_type == "bonded"),
            address=address,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_warehouse(warehouse)
        self.repo.flush()

        building = Building(
            organization_id=org_id, warehouse_id=warehouse.id, code=building_code, name=building_code, created_at=now
        )
        self.repo.add_building(building)
        self.repo.flush()
        store = StoreArea(
            organization_id=org_id, building_id=building.id, code=store_code, name=store_code, created_at=now
        )
        self.repo.add_store_area(store)
        self.repo.flush()
        room = Room(organization_id=org_id, store_id=store.id, code=room_code, name=room_code, created_at=now)
        self.repo.add_room(room)
        self.repo.flush()

        locations: list[Location] = []
        for zone_type in zone_types:
            zone_code = f"Z-{zone_type[:4].upper()}"
            zone = Zone(
                organization_id=org_id,
                room_id=room.id,
                code=zone_code,
                name=zone_type.replace("_", " ").title(),
                zone_type=zone_type,
                created_at=now,
            )
            self.repo.add_zone(zone)
            self.repo.flush()
            aisle = Aisle(organization_id=org_id, zone_id=zone.id, code=f"{zone_code}-A1", created_at=now)
            self.repo.add_aisle(aisle)
            self.repo.flush()
            shelf = Shelf(organization_id=org_id, aisle_id=aisle.id, code=f"{zone_code}-A1-S1", created_at=now)
            self.repo.add_shelf(shelf)
            self.repo.flush()
            for index in range(1, bins_per_zone + 1):
                bin_code = f"{zone_code}-A1-S1-B{index:02d}"
                bin_row = Bin(organization_id=org_id, shelf_id=shelf.id, code=bin_code, created_at=now)
                self.repo.add_bin(bin_row)
                self.repo.flush()
                location = Location(
                    organization_id=org_id,
                    warehouse_id=warehouse.id,
                    building_id=building.id,
                    store_id=store.id,
                    room_id=room.id,
                    zone_id=zone.id,
                    aisle_id=aisle.id,
                    shelf_id=shelf.id,
                    bin_id=bin_row.id,
                    location_code=f"{code}-{bin_code}",
                    location_type=zone_type,
                    status="active",
                    created_at=now,
                )
                self.repo.add_location(location)
                locations.append(location)
        self.repo.flush()
        return warehouse, locations

    def create_location(self, payload: LocationCreate, actor: ActorContext) -> LocationOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        self._require_warehouse(org_id, payload.warehouse_id)
        location_code = payload.location_code.strip().upper()
        if self.repo.get_location_by_code(org_id, location_code) is not None:
            raise HTTPException(status_code=409, detail="Location code already exists")
        row = Location(
            organization_id=org_id,
            warehouse_id=payload.warehouse_id,
            building_id=payload.building_id,
            store_id=payload.store_id,
            room_id=payload.room_id,
            zone_id=payload.zone_id,
            aisle_id=payload.aisle_id,
            shelf_id=payload.shelf_id,
            bin_id=payload.bin_id,
            location_code=location_code,
            location_type=payload.location_type,
            status="active",
            created_at=_utcnow(),
        )
        self.repo.add_location(row)
        self._commit_or_conflict(detail="Location conflict")
        self.repo.refresh(row)
        return LocationOut.model_validate(row)

    def list_locations(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        warehouse_id: str | None = None,
        location_type: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[LocationOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            LocationOut.model_validate(r)
            for r in self.repo.list_locations(
                organization_id=org_id,
                warehouse_id=warehouse_id,
                location_type=location_type,
                limit=limit,
                offset=offset,
            )
        ]

    # ------------------------------------------------------------------
    # Part master
    # ------------------------------------------------------------------
    def create_part(self, payload: PartMasterCreate, actor: ActorContext) -> PartMasterOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        oem = payload.oem_part_number.strip().upper()
        if self.repo.get_part_by_number(org_id, oem) is not None:
            raise HTTPException(status_code=409, detail="Part number already exists")
        now = _utcnow()
        row = PartMaster(
            organization_id=org_id,
            catalog_item_id=payload.catalog_item_id,
            manufacturer=(payload.manufacturer or "").strip(),
            oem_part_number=oem,
            customer_part_number=(payload.customer_part_number or "").strip().upper(),
            description=(payload.description or "").strip(),
            ata_chapter_id=payload.ata_chapter_id,
            nsn=(payload.nsn or "").strip(),
            part_class=payload.part_class,
            is_serialized=_flag(payload.is_serialized or payload.part_class == "rotable"),
            is_life_limited=_flag(payload.is_life_limited),
            weight_kg=payload.weight_kg,
            length_mm=payload.length_mm,
            width_mm=payload.width_mm,
            height_mm=payload.height_mm,
            shelf_life_days=payload.shelf_life_days,
            is_hazmat=_flag(payload.is_hazmat),
            is_dangerous_goods=_flag(payload.is_dangerous_goods),
            is_rohs=_flag(payload.is_rohs),
            issue_policy=payload.issue_policy,
            min_stock=payload.min_stock,
            max_stock=payload.max_stock,
            reorder_point=payload.reorder_point,
            unit_of_measure=(payload.unit_of_measure or "EA").strip().upper(),
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_part(row)
        self._audit_required(
            actor,
            action="logistics.part.create",
            target_type="logistics_part_master",
            target_id=row.id,
            organization_id=org_id,
            details=f"pn={oem}",
        )
        self._commit_or_conflict(detail="Part conflict")
        self.repo.refresh(row)
        return PartMasterOut.model_validate(row)

    def update_part(self, part_id: str, payload: PartMasterUpdate, actor: ActorContext) -> PartMasterOut:
        org_id = self.resolve_org_id(actor)
        row = self._require_part(org_id, part_id, for_update=True)
        data = payload.model_dump(exclude_unset=True, exclude_none=True)
        for field in (
            "description",
            "manufacturer",
            "customer_part_number",
            "ata_chapter_id",
            "nsn",
            "part_class",
            "shelf_life_days",
            "issue_policy",
            "min_stock",
            "max_stock",
            "reorder_point",
            "unit_of_measure",
            "status",
        ):
            if field in data:
                setattr(row, field, data[field])
        row.updated_at = _utcnow()
        self._commit_or_conflict(detail="Part update conflict")
        self.repo.refresh(row)
        return PartMasterOut.model_validate(row)

    def get_part(self, part_id: str, actor: ActorContext) -> PartMasterOut:
        org_id = self.resolve_org_id(actor)
        return PartMasterOut.model_validate(self._require_part(org_id, part_id))

    def list_parts(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        q: str | None = None,
        part_class: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartMasterOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            PartMasterOut.model_validate(r)
            for r in self.repo.list_parts(
                organization_id=org_id, q=q, part_class=part_class, status=status, limit=limit, offset=offset
            )
        ]

    def add_identifier(self, payload: IdentifierCreate, actor: ActorContext) -> IdentifierOut:
        org_id = self.resolve_org_id(actor)
        if not (payload.part_master_id or payload.stock_unit_id or payload.tool_id):
            raise HTTPException(status_code=400, detail="Identifier must target a part, stock unit or tool")
        if payload.part_master_id:
            self._require_part(org_id, payload.part_master_id)
        if payload.stock_unit_id:
            self._require_stock_unit(org_id, payload.stock_unit_id)
        if payload.tool_id:
            self._require_tool(org_id, payload.tool_id)
        value = payload.value.strip()
        if self.repo.get_identifier(org_id, value, identifier_type=payload.identifier_type) is not None:
            raise HTTPException(status_code=409, detail="Identifier value already registered")
        row = PartIdentifier(
            organization_id=org_id,
            part_master_id=payload.part_master_id,
            stock_unit_id=payload.stock_unit_id,
            tool_id=payload.tool_id,
            identifier_type=payload.identifier_type,
            value=value,
            status="active",
            created_at=_utcnow(),
        )
        self.repo.add_identifier(row)
        self._commit_or_conflict(detail="Identifier conflict")
        self.repo.refresh(row)
        return IdentifierOut.model_validate(row)

    def list_identifiers(self, part_id: str, actor: ActorContext) -> list[IdentifierOut]:
        org_id = self.resolve_org_id(actor)
        self._require_part(org_id, part_id)
        return [
            IdentifierOut.model_validate(r)
            for r in self.repo.list_identifiers(organization_id=org_id, part_master_id=part_id)
        ]

    def add_attachment(self, part_id: str, payload: AttachmentCreate, actor: ActorContext) -> AttachmentOut:
        org_id = self.resolve_org_id(actor)
        self._require_part(org_id, part_id)
        row = PartAttachment(
            organization_id=org_id,
            part_master_id=part_id,
            attachment_type=payload.attachment_type,
            title=(payload.title or "").strip(),
            uri=payload.uri.strip(),
            content_type=(payload.content_type or "").strip(),
            created_at=_utcnow(),
        )
        self.repo.add_attachment(row)
        self._commit_or_conflict(detail="Attachment conflict")
        self.repo.refresh(row)
        return AttachmentOut.model_validate(row)

    def list_attachments(self, part_id: str, actor: ActorContext) -> list[AttachmentOut]:
        org_id = self.resolve_org_id(actor)
        self._require_part(org_id, part_id)
        return [
            AttachmentOut.model_validate(r)
            for r in self.repo.list_attachments(organization_id=org_id, part_master_id=part_id)
        ]

    def create_family(self, payload: FamilyCreate, actor: ActorContext) -> FamilyOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        code = payload.code.strip().upper()
        if self.repo.get_family_by_code(org_id, code) is not None:
            raise HTTPException(status_code=409, detail="Family code already exists")
        row = PartFamily(
            organization_id=org_id,
            code=code,
            name=payload.name.strip(),
            status="active",
            created_at=_utcnow(),
        )
        self.repo.add_family(row)
        self.repo.flush()
        for part_id in payload.part_master_ids:
            self._require_part(org_id, part_id)
            self.repo.add_family_member(
                PartFamilyMember(organization_id=org_id, family_id=row.id, part_master_id=part_id)
            )
        self._commit_or_conflict(detail="Part family conflict")
        self.repo.refresh(row)
        return FamilyOut.model_validate(row)

    def list_families(
        self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[FamilyOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            FamilyOut.model_validate(r)
            for r in self.repo.list_families(organization_id=org_id, limit=limit, offset=offset)
        ]

    def list_family_members(self, family_id: str, actor: ActorContext) -> list[FamilyMemberOut]:
        org_id = self.resolve_org_id(actor)
        if self.repo.get_family(org_id, family_id) is None:
            raise HTTPException(status_code=404, detail="Part family not found")
        return [
            FamilyMemberOut.model_validate(r)
            for r in self.repo.list_family_members(organization_id=org_id, family_id=family_id)
        ]

    def add_supersession(self, payload: SupersessionCreate, actor: ActorContext) -> SupersessionOut:
        org_id = self.resolve_org_id(actor)
        if payload.from_part_id == payload.to_part_id:
            raise HTTPException(status_code=400, detail="Supersession requires two distinct parts")
        self._require_part(org_id, payload.from_part_id)
        self._require_part(org_id, payload.to_part_id)
        row = PartSupersession(
            organization_id=org_id,
            from_part_id=payload.from_part_id,
            to_part_id=payload.to_part_id,
            relation_type=payload.relation_type,
            notes=(payload.notes or "").strip(),
            status="active",
            created_at=_utcnow(),
        )
        self.repo.add_supersession(row)
        self._commit_or_conflict(detail="Supersession already recorded")
        self.repo.refresh(row)
        return SupersessionOut.model_validate(row)

    def list_supersessions(
        self, actor: ActorContext, *, organization_id: str | None = None, part_master_id: str | None = None
    ) -> list[SupersessionOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            SupersessionOut.model_validate(r)
            for r in self.repo.list_supersessions(organization_id=org_id, part_master_id=part_master_id)
        ]

    # ------------------------------------------------------------------
    # Stock primitives
    # ------------------------------------------------------------------
    def _movement(
        self,
        org_id: str,
        *,
        movement_type: str,
        part_master_id: str,
        qty: Decimal,
        condition: str,
        performed_by: str,
        stock_unit_id: str | None = None,
        from_location_id: str | None = None,
        to_location_id: str | None = None,
        reference_type: str = "",
        reference_id: str = "",
        notes: str = "",
        now: datetime | None = None,
    ) -> StockMovement:
        row = StockMovement(
            organization_id=org_id,
            movement_type=movement_type,
            part_master_id=part_master_id,
            stock_unit_id=stock_unit_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            qty=qty,
            condition=condition,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            performed_by=performed_by,
            created_at=now or _utcnow(),
        )
        self.repo.add_movement(row)
        return row

    def _receive_into_stock(
        self,
        org_id: str,
        *,
        part: PartMaster,
        location: Location,
        qty: Decimal,
        condition: str,
        performed_by: str,
        serial_number: str = "",
        batch_number: str = "",
        lot_number: str = "",
        expires_at: datetime | None = None,
        warranty_expires_at: datetime | None = None,
        reference_type: str = "",
        reference_id: str = "",
        notes: str = "",
        now: datetime | None = None,
    ) -> StockUnit:
        moment = now or _utcnow()
        expiry = expires_at
        if expiry is None and part.shelf_life_days:
            expiry = moment + timedelta(days=int(part.shelf_life_days))
        unit = StockUnit(
            organization_id=org_id,
            part_master_id=part.id,
            serial_number=(serial_number or "").strip(),
            batch_number=(batch_number or "").strip(),
            lot_number=(lot_number or "").strip(),
            location_id=location.id,
            warehouse_id=location.warehouse_id,
            condition=condition,
            qty=qty,
            received_at=moment,
            expires_at=expiry,
            warranty_expires_at=warranty_expires_at,
            status="active",
            created_at=moment,
            updated_at=moment,
        )
        self.repo.add_stock_unit(unit)
        self.repo.flush()
        balance = self.repo.get_or_create_balance(org_id, part.id, location.id, condition, now=moment)
        balance.qty_on_hand = _dec(balance.qty_on_hand) + qty
        balance.updated_at = moment
        self._movement(
            org_id,
            movement_type="receive",
            part_master_id=part.id,
            qty=qty,
            condition=condition,
            performed_by=performed_by,
            stock_unit_id=unit.id,
            to_location_id=location.id,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            now=moment,
        )
        return unit

    def _consume_units(
        self, org_id: str, part: PartMaster, location_id: str, condition: str, qty: Decimal, now: datetime
    ) -> list[tuple[StockUnit, Decimal]]:
        """Draw `qty` from lot/serial units at a location using the part issue policy."""
        remaining = qty
        taken: list[tuple[StockUnit, Decimal]] = []
        units = self.repo.pickable_units(
            organization_id=org_id,
            part_master_id=part.id,
            location_id=location_id,
            condition=condition,
            policy=part.issue_policy or "FEFO",
        )
        for unit in units:
            if remaining <= ZERO:
                break
            available = _dec(unit.qty)
            if available <= ZERO:
                continue
            take = available if available < remaining else remaining
            unit.qty = available - take
            unit.updated_at = now
            if unit.qty <= ZERO:
                unit.status = "consumed"
            taken.append((unit, take))
            remaining -= take
        return taken

    def _withdraw(
        self,
        org_id: str,
        *,
        part: PartMaster,
        qty: Decimal,
        condition: str,
        performed_by: str,
        movement_type: str,
        location_id: str | None = None,
        from_reserved: Decimal = ZERO,
        reference_type: str = "",
        reference_id: str = "",
        notes: str = "",
        now: datetime | None = None,
    ) -> list[tuple[StockBalance, Decimal]]:
        """Remove stock across one or more balances honouring FIFO/FEFO on lots."""
        moment = now or _utcnow()
        if location_id:
            balance = self.repo.get_balance(org_id, part.id, location_id, condition)
            candidates = [balance] if balance is not None else []
        else:
            candidates = list(self.repo.balances_with_availability(org_id, part.id, condition=condition))
        if not candidates:
            raise HTTPException(status_code=409, detail="No stock available for part")

        total_available = ZERO
        for balance in candidates:
            total_available += _dec(balance.qty_on_hand) - _dec(balance.qty_reserved)
        total_available += from_reserved
        if total_available < qty:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient available stock: requested {qty}, available {total_available}",
            )

        remaining = qty
        reserved_credit = from_reserved
        drawn: list[tuple[StockBalance, Decimal]] = []
        for balance in candidates:
            if remaining <= ZERO:
                break
            free = _dec(balance.qty_on_hand) - _dec(balance.qty_reserved)
            if reserved_credit > ZERO:
                credit = reserved_credit if reserved_credit < _dec(balance.qty_reserved) else _dec(balance.qty_reserved)
                free += credit
            else:
                credit = ZERO
            if free <= ZERO:
                continue
            take = free if free < remaining else remaining
            used_reserved = credit if credit < take else take
            balance.qty_on_hand = _dec(balance.qty_on_hand) - take
            if used_reserved > ZERO:
                balance.qty_reserved = _dec(balance.qty_reserved) - used_reserved
                reserved_credit -= used_reserved
            balance.updated_at = moment
            consumed = self._consume_units(org_id, part, balance.location_id, condition, take, moment)
            if consumed:
                for unit, unit_qty in consumed:
                    self._movement(
                        org_id,
                        movement_type=movement_type,
                        part_master_id=part.id,
                        qty=unit_qty,
                        condition=condition,
                        performed_by=performed_by,
                        stock_unit_id=unit.id,
                        from_location_id=balance.location_id,
                        reference_type=reference_type,
                        reference_id=reference_id,
                        notes=notes,
                        now=moment,
                    )
            else:
                self._movement(
                    org_id,
                    movement_type=movement_type,
                    part_master_id=part.id,
                    qty=take,
                    condition=condition,
                    performed_by=performed_by,
                    from_location_id=balance.location_id,
                    reference_type=reference_type,
                    reference_id=reference_id,
                    notes=notes,
                    now=moment,
                )
            drawn.append((balance, take))
            remaining -= take
        if remaining > ZERO:
            raise HTTPException(status_code=409, detail="Insufficient available stock at selected locations")
        return drawn

    def _reserve(
        self,
        org_id: str,
        *,
        part: PartMaster,
        qty: Decimal,
        performed_by: str,
        location_id: str | None = None,
        stock_unit_id: str | None = None,
        source_type: str = "manual",
        source_id: str = "",
        parts_plan_line_id: str | None = None,
        condition: str = "serviceable",
        now: datetime | None = None,
    ) -> StockReservation:
        moment = now or _utcnow()
        if location_id:
            balance = self.repo.get_balance(org_id, part.id, location_id, condition)
            candidates = [balance] if balance is not None else []
        else:
            candidates = list(self.repo.balances_with_availability(org_id, part.id, condition=condition))
        available = sum((_dec(b.qty_on_hand) - _dec(b.qty_reserved) for b in candidates), ZERO)
        if available < qty:
            raise HTTPException(
                status_code=409, detail=f"Insufficient stock to reserve: requested {qty}, available {available}"
            )
        target = next((b for b in candidates if (_dec(b.qty_on_hand) - _dec(b.qty_reserved)) >= qty), None)
        if target is None:
            raise HTTPException(
                status_code=409, detail="Requested quantity is split across locations; reserve per location"
            )
        target.qty_reserved = _dec(target.qty_reserved) + qty
        target.updated_at = moment
        reservation = StockReservation(
            organization_id=org_id,
            part_master_id=part.id,
            location_id=target.location_id,
            stock_unit_id=stock_unit_id,
            qty=qty,
            status="open",
            source_type=source_type,
            source_id=source_id,
            parts_plan_line_id=parts_plan_line_id,
            created_by=performed_by,
            created_at=moment,
        )
        self.repo.add_reservation(reservation)
        self.repo.flush()
        self._movement(
            org_id,
            movement_type="reservation",
            part_master_id=part.id,
            qty=qty,
            condition=condition,
            performed_by=performed_by,
            to_location_id=target.location_id,
            reference_type=source_type,
            reference_id=source_id or reservation.id,
            notes="stock reserved",
            now=moment,
        )
        return reservation

    def _release(self, org_id: str, reservation: StockReservation, *, performed_by: str, now: datetime) -> None:
        if reservation.status != "open":
            return
        if reservation.location_id:
            balance = self.repo.get_balance(org_id, reservation.part_master_id, reservation.location_id, "serviceable")
            if balance is not None:
                remaining = _dec(balance.qty_reserved) - _dec(reservation.qty)
                balance.qty_reserved = remaining if remaining > ZERO else ZERO
                balance.updated_at = now
        reservation.status = "released"
        reservation.released_at = now
        self._movement(
            org_id,
            movement_type="release",
            part_master_id=reservation.part_master_id,
            qty=_dec(reservation.qty),
            condition="serviceable",
            performed_by=performed_by,
            from_location_id=reservation.location_id,
            reference_type=reservation.source_type,
            reference_id=reservation.source_id or reservation.id,
            notes="reservation released",
            now=now,
        )

    # ------------------------------------------------------------------
    # Stock operations (public)
    # ------------------------------------------------------------------
    def receive_stock(self, payload: ReceiveStockRequest, actor: ActorContext) -> StockUnitOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        part = self._require_part(org_id, payload.part_master_id)
        location = self._require_location(org_id, payload.location_id)
        unit = self._receive_into_stock(
            org_id,
            part=part,
            location=location,
            qty=_dec(payload.qty),
            condition=payload.condition,
            performed_by=actor.username,
            serial_number=payload.serial_number,
            batch_number=payload.batch_number,
            lot_number=payload.lot_number,
            expires_at=payload.expires_at,
            warranty_expires_at=payload.warranty_expires_at,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
            notes=payload.notes,
        )
        self._audit_required(
            actor,
            action="logistics.stock.receive",
            target_type="logistics_stock_unit",
            target_id=unit.id,
            organization_id=org_id,
            details=f"part={part.oem_part_number};qty={payload.qty};location={location.location_code}",
        )
        self._commit_or_conflict(detail="Stock receive conflict")
        self.repo.refresh(unit)
        return StockUnitOut.model_validate(unit)

    def issue_stock(self, payload: IssueStockRequest, actor: ActorContext) -> list[StockMovementOut]:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        part = self._require_part(org_id, payload.part_master_id)
        qty = _dec(payload.qty)
        now = _utcnow()
        location_id = payload.location_id
        from_reserved = ZERO
        reservation: StockReservation | None = None
        if payload.reservation_id:
            reservation = self.repo.get_reservation(org_id, payload.reservation_id, for_update=True)
            if reservation is None:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if reservation.status != "open":
                raise HTTPException(status_code=409, detail=f"Reservation is '{reservation.status}'")
            if reservation.part_master_id != part.id:
                raise HTTPException(status_code=409, detail="Reservation is for a different part")
            if _dec(reservation.qty) < qty:
                raise HTTPException(status_code=409, detail="Issue quantity exceeds reservation")
            location_id = reservation.location_id or location_id
            from_reserved = qty
        if location_id:
            self._require_location(org_id, location_id)
        self._withdraw(
            org_id,
            part=part,
            qty=qty,
            condition=payload.condition,
            performed_by=actor.username,
            movement_type="issue",
            location_id=location_id,
            from_reserved=from_reserved,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
            notes=payload.notes,
            now=now,
        )
        if reservation is not None:
            reservation.qty = _dec(reservation.qty) - qty
            if _dec(reservation.qty) <= ZERO:
                reservation.status = "issued"
                reservation.released_at = now
        self._audit_required(
            actor,
            action="logistics.stock.issue",
            target_type="logistics_part_master",
            target_id=part.id,
            organization_id=org_id,
            details=f"pn={part.oem_part_number};qty={qty};policy={part.issue_policy}",
        )
        self._commit_or_conflict(detail="Stock issue conflict")
        return [
            StockMovementOut.model_validate(m)
            for m in self.repo.list_movements(
                organization_id=org_id, part_master_id=part.id, movement_type="issue", since=now, limit=100
            )
        ]

    def adjust_stock(self, payload: AdjustStockRequest, actor: ActorContext) -> StockBalanceDetailOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        part = self._require_part(org_id, payload.part_master_id)
        location = self._require_location(org_id, payload.location_id)
        delta = _dec(payload.qty_delta)
        if delta == ZERO:
            raise HTTPException(status_code=400, detail="Adjustment quantity must not be zero")
        now = _utcnow()
        balance = self.repo.get_or_create_balance(org_id, part.id, location.id, payload.condition, now=now)
        new_qty = _dec(balance.qty_on_hand) + delta
        if new_qty < ZERO:
            raise HTTPException(status_code=409, detail="Adjustment would drive stock negative")
        if new_qty < _dec(balance.qty_reserved):
            raise HTTPException(status_code=409, detail="Adjustment would drop below reserved quantity")
        balance.qty_on_hand = new_qty
        balance.updated_at = now
        self._movement(
            org_id,
            movement_type="adjust",
            part_master_id=part.id,
            qty=delta,
            condition=payload.condition,
            performed_by=actor.username,
            to_location_id=location.id if delta > ZERO else None,
            from_location_id=location.id if delta < ZERO else None,
            reference_type="adjust",
            reference_id=balance.id,
            notes=payload.reason,
            now=now,
        )
        if delta < ZERO:
            self._consume_units(org_id, part, location.id, payload.condition, -delta, now)
        self._audit_required(
            actor,
            action="logistics.stock.adjust",
            target_type="logistics_stock_balance",
            target_id=balance.id,
            organization_id=org_id,
            details=f"pn={part.oem_part_number};delta={delta};reason={payload.reason[:120]}",
        )
        self._commit_or_conflict(detail="Stock adjust conflict")
        self.repo.refresh(balance)
        return self._balance_detail(balance, part, location)

    def bulk_adjust(self, payload: BulkAdjustRequest, actor: ActorContext) -> BulkAdjustResult:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        now = _utcnow()
        results: list[BulkAdjustResultLine] = []
        applied = 0
        for line in payload.lines:
            part = self.repo.get_part(org_id, line.part_master_id)
            location = self.repo.get_location(org_id, line.location_id)
            if part is None or location is None:
                results.append(
                    BulkAdjustResultLine(
                        part_master_id=line.part_master_id,
                        location_id=line.location_id,
                        condition=line.condition,
                        qty_delta=_dec(line.qty_delta),
                        qty_on_hand=ZERO,
                        applied=False,
                        message="Part or location not found in organization",
                    )
                )
                continue
            balance = self.repo.get_or_create_balance(org_id, part.id, location.id, line.condition, now=now)
            delta = _dec(line.qty_delta)
            new_qty = _dec(balance.qty_on_hand) + delta
            if delta == ZERO or new_qty < ZERO or new_qty < _dec(balance.qty_reserved):
                results.append(
                    BulkAdjustResultLine(
                        part_master_id=part.id,
                        location_id=location.id,
                        condition=line.condition,
                        qty_delta=delta,
                        qty_on_hand=_dec(balance.qty_on_hand),
                        applied=False,
                        message="Rejected: zero delta or would violate on-hand/reserved invariants",
                    )
                )
                continue
            balance.qty_on_hand = new_qty
            balance.updated_at = now
            self._movement(
                org_id,
                movement_type="adjust",
                part_master_id=part.id,
                qty=delta,
                condition=line.condition,
                performed_by=actor.username,
                to_location_id=location.id if delta > ZERO else None,
                from_location_id=location.id if delta < ZERO else None,
                reference_type="adjust",
                reference_id=balance.id,
                notes=payload.reason,
                now=now,
            )
            if delta < ZERO:
                self._consume_units(org_id, part, location.id, line.condition, -delta, now)
            applied += 1
            results.append(
                BulkAdjustResultLine(
                    part_master_id=part.id,
                    location_id=location.id,
                    condition=line.condition,
                    qty_delta=delta,
                    qty_on_hand=new_qty,
                    applied=True,
                )
            )
        self._audit_required(
            actor,
            action="logistics.stock.bulk_adjust",
            target_type="logistics_stock_balance",
            target_id=org_id,
            organization_id=org_id,
            details=f"applied={applied};rejected={len(results) - applied};reason={payload.reason[:120]}",
        )
        self._commit_or_conflict(detail="Bulk adjust conflict")
        return BulkAdjustResult(applied=applied, rejected=len(results) - applied, lines=results)

    def scrap_stock(self, payload: ScrapStockRequest, actor: ActorContext) -> StockBalanceDetailOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        part = self._require_part(org_id, payload.part_master_id)
        location = self._require_location(org_id, payload.location_id)
        now = _utcnow()
        if payload.stock_unit_id:
            unit = self._require_stock_unit(org_id, payload.stock_unit_id, for_update=True)
            unit.condition = "scrap"
            unit.status = "scrapped"
            unit.updated_at = now
        self._withdraw(
            org_id,
            part=part,
            qty=_dec(payload.qty),
            condition=payload.condition,
            performed_by=actor.username,
            movement_type="scrap",
            location_id=location.id,
            reference_type="scrap",
            reference_id=payload.stock_unit_id or "",
            notes=payload.reason,
            now=now,
        )
        self._audit_required(
            actor,
            action="logistics.stock.scrap",
            target_type="logistics_part_master",
            target_id=part.id,
            organization_id=org_id,
            details=f"pn={part.oem_part_number};qty={payload.qty};reason={payload.reason[:120]}",
        )
        self._commit_or_conflict(detail="Scrap conflict")
        balance = self.repo.get_or_create_balance(org_id, part.id, location.id, payload.condition, now=now)
        return self._balance_detail(balance, part, location)

    def reserve_stock(self, payload: ReservationCreate, actor: ActorContext) -> ReservationOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        part = self._require_part(org_id, payload.part_master_id)
        if payload.location_id:
            self._require_location(org_id, payload.location_id)
        reservation = self._reserve(
            org_id,
            part=part,
            qty=_dec(payload.qty),
            performed_by=actor.username,
            location_id=payload.location_id,
            stock_unit_id=payload.stock_unit_id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            parts_plan_line_id=payload.parts_plan_line_id,
        )
        self._commit_or_conflict(detail="Reservation conflict")
        self.repo.refresh(reservation)
        return ReservationOut.model_validate(reservation)

    def release_reservation(self, reservation_id: str, actor: ActorContext) -> ReservationOut:
        org_id = self.resolve_org_id(actor)
        reservation = self.repo.get_reservation(org_id, reservation_id, for_update=True)
        if reservation is None:
            raise HTTPException(status_code=404, detail="Reservation not found")
        if reservation.status != "open":
            raise HTTPException(status_code=409, detail=f"Reservation is '{reservation.status}'")
        self._release(org_id, reservation, performed_by=actor.username, now=_utcnow())
        self._commit_or_conflict(detail="Reservation release conflict")
        self.repo.refresh(reservation)
        return ReservationOut.model_validate(reservation)

    def list_reservations(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        part_master_id: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[ReservationOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            ReservationOut.model_validate(r)
            for r in self.repo.list_reservations(
                organization_id=org_id,
                status=status,
                source_type=source_type,
                source_id=source_id,
                part_master_id=part_master_id,
                limit=limit,
                offset=offset,
            )
        ]

    @staticmethod
    def _balance_detail(balance: StockBalance, part: PartMaster, location: Location) -> StockBalanceDetailOut:
        out = StockBalanceDetailOut.model_validate(balance)
        out.part_number = part.oem_part_number
        out.part_description = part.description or ""
        out.location_code = location.location_code
        out.qty_available = _dec(balance.qty_on_hand) - _dec(balance.qty_reserved)
        return out

    def list_balances(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        part_master_id: str | None = None,
        location_id: str | None = None,
        condition: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[StockBalanceDetailOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        rows = self.repo.list_balances_detailed(
            organization_id=org_id,
            part_master_id=part_master_id,
            location_id=location_id,
            condition=condition,
            limit=limit,
            offset=offset,
        )
        return [self._balance_detail(balance, part, location) for balance, part, location in rows]

    def list_stock_units(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        part_master_id: str | None = None,
        location_id: str | None = None,
        condition: str | None = None,
        serial_number: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[StockUnitOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            StockUnitOut.model_validate(r)
            for r in self.repo.list_stock_units(
                organization_id=org_id,
                part_master_id=part_master_id,
                location_id=location_id,
                condition=condition,
                serial_number=serial_number,
                limit=limit,
                offset=offset,
            )
        ]

    def list_movements(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        part_master_id: str | None = None,
        movement_type: str | None = None,
        reference_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StockMovementOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            StockMovementOut.model_validate(r)
            for r in self.repo.list_movements(
                organization_id=org_id,
                part_master_id=part_master_id,
                movement_type=movement_type,
                reference_id=reference_id,
                limit=limit,
                offset=offset,
            )
        ]

    # ------------------------------------------------------------------
    # Warehouse transfers
    # ------------------------------------------------------------------
    def create_transfer(self, payload: TransferCreate, actor: ActorContext) -> TransferDetailOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        self._require_warehouse(org_id, payload.from_warehouse_id)
        self._require_warehouse(org_id, payload.to_warehouse_id)
        if payload.from_warehouse_id == payload.to_warehouse_id:
            raise HTTPException(status_code=400, detail="Transfer requires two distinct warehouses")
        if payload.from_location_id:
            self._require_location(org_id, payload.from_location_id)
        if payload.to_location_id:
            self._require_location(org_id, payload.to_location_id)
        now = _utcnow()
        transfer = WarehouseTransfer(
            organization_id=org_id,
            transfer_number=_number("TR"),
            from_warehouse_id=payload.from_warehouse_id,
            to_warehouse_id=payload.to_warehouse_id,
            from_location_id=payload.from_location_id,
            to_location_id=payload.to_location_id,
            status="in_transit" if payload.lines else "draft",
            notes=(payload.notes or "").strip(),
            created_by=actor.username,
            created_at=now,
        )
        self.repo.add_transfer(transfer)
        self.repo.flush()
        lines: list[WarehouseTransferLine] = []
        for line in payload.lines:
            self._require_part(org_id, line.part_master_id)
            row = WarehouseTransferLine(
                organization_id=org_id,
                transfer_id=transfer.id,
                part_master_id=line.part_master_id,
                stock_unit_id=line.stock_unit_id,
                qty=_dec(line.qty),
                status="pending",
            )
            self.repo.add_transfer_line(row)
            lines.append(row)
        self._commit_or_conflict(detail="Transfer conflict")
        self.repo.refresh(transfer)
        return TransferDetailOut(
            **TransferOut.model_validate(transfer).model_dump(),
            lines=[TransferLineOut.model_validate(r) for r in lines],
        )

    def complete_transfer(
        self, transfer_id: str, payload: TransferCompleteRequest, actor: ActorContext
    ) -> TransferDetailOut:
        org_id = self.resolve_org_id(actor)
        transfer = self.repo.get_transfer(org_id, transfer_id, for_update=True)
        if transfer is None:
            raise HTTPException(status_code=404, detail="Transfer not found")
        if transfer.status not in {"draft", "in_transit"}:
            raise HTTPException(status_code=409, detail=f"Cannot complete transfer in status '{transfer.status}'")
        lines = self.repo.list_transfer_lines(organization_id=org_id, transfer_id=transfer.id)
        if not lines:
            raise HTTPException(status_code=409, detail="Transfer has no lines")
        target_location_id = payload.to_location_id or transfer.to_location_id
        if target_location_id:
            target = self._require_location(org_id, target_location_id)
        else:
            target = self.repo.first_location_of_type(org_id, "general")
            if target is None or target.warehouse_id != transfer.to_warehouse_id:
                candidates = self.repo.list_locations(
                    organization_id=org_id, warehouse_id=transfer.to_warehouse_id, limit=1
                )
                target = candidates[0] if candidates else None
        if target is None:
            raise HTTPException(status_code=409, detail="Destination warehouse has no location")
        if target.warehouse_id != transfer.to_warehouse_id:
            raise HTTPException(status_code=409, detail="Destination location is not in the destination warehouse")

        now = _utcnow()
        for line in lines:
            part = self._require_part(org_id, line.part_master_id)
            qty = _dec(line.qty)
            source_location_id = transfer.from_location_id
            if source_location_id is None:
                source_balances = self.repo.balances_in_warehouse(
                    org_id, part.id, transfer.from_warehouse_id, condition="serviceable"
                )
                if not source_balances:
                    raise HTTPException(
                        status_code=409, detail=f"No available stock in source warehouse for {part.oem_part_number}"
                    )
                source_location_id = source_balances[0].location_id
            self._withdraw(
                org_id,
                part=part,
                qty=qty,
                condition="serviceable",
                performed_by=actor.username,
                movement_type="transfer",
                location_id=source_location_id,
                reference_type="transfer",
                reference_id=transfer.id,
                notes=f"transfer {transfer.transfer_number}",
                now=now,
            )
            balance = self.repo.get_or_create_balance(org_id, part.id, target.id, "serviceable", now=now)
            balance.qty_on_hand = _dec(balance.qty_on_hand) + qty
            balance.updated_at = now
            self._movement(
                org_id,
                movement_type="transfer",
                part_master_id=part.id,
                qty=qty,
                condition="serviceable",
                performed_by=actor.username,
                from_location_id=source_location_id,
                to_location_id=target.id,
                reference_type="transfer",
                reference_id=transfer.id,
                notes=f"transfer {transfer.transfer_number} inbound",
                now=now,
            )
            line.status = "completed"
        transfer.status = "completed"
        transfer.to_location_id = target.id
        transfer.completed_at = now
        if payload.notes:
            transfer.notes = f"{transfer.notes}\n{payload.notes}".strip()
        self._audit_required(
            actor,
            action="logistics.transfer.complete",
            target_type="logistics_warehouse_transfer",
            target_id=transfer.id,
            organization_id=org_id,
            details=f"number={transfer.transfer_number};lines={len(lines)}",
        )
        self._commit_or_conflict(detail="Transfer completion conflict")
        self.repo.refresh(transfer)
        return TransferDetailOut(
            **TransferOut.model_validate(transfer).model_dump(),
            lines=[TransferLineOut.model_validate(r) for r in lines],
        )

    def list_transfers(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TransferOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            TransferOut.model_validate(r)
            for r in self.repo.list_transfers(organization_id=org_id, status=status, limit=limit, offset=offset)
        ]

    # ------------------------------------------------------------------
    # Rotable cycles
    # ------------------------------------------------------------------
    def open_rotable_cycle(self, payload: RotableCycleCreate, actor: ActorContext) -> RotableCycleOut:
        org_id = self.resolve_org_id(actor)
        unit = self._require_stock_unit(org_id, payload.stock_unit_id, for_update=True)
        if payload.vendor_id:
            self._require_vendor(org_id, payload.vendor_id)
        open_cycles = self.repo.list_rotable_cycles(
            organization_id=org_id, status="open", stock_unit_id=unit.id, limit=1
        )
        if open_cycles:
            raise HTTPException(status_code=409, detail="Stock unit already has an open rotable cycle")
        now = _utcnow()
        row = RotableCycle(
            organization_id=org_id,
            stock_unit_id=unit.id,
            cycle_type=payload.cycle_type,
            vendor_id=payload.vendor_id,
            status="in_repair" if payload.cycle_type == "repair" else "open",
            warranty_claim=_flag(payload.warranty_claim),
            notes=(payload.notes or "").strip(),
            opened_at=now,
            created_by=actor.username,
        )
        self.repo.add_rotable_cycle(row)
        if payload.cycle_type in {"repair", "core_return", "exchange"}:
            unit.condition = "repair"
        elif payload.cycle_type in {"loan", "rental"}:
            unit.condition = "loaned"
            unit.is_loan = _flag(payload.cycle_type == "loan")
            unit.is_rental = _flag(payload.cycle_type == "rental")
        elif payload.cycle_type == "pool":
            unit.condition = "pooled"
            unit.is_pool = "true"
        unit.updated_at = now
        self._commit_or_conflict(detail="Rotable cycle conflict")
        self.repo.refresh(row)
        return RotableCycleOut.model_validate(row)

    def close_rotable_cycle(
        self, cycle_id: str, payload: RotableCycleCloseRequest, actor: ActorContext
    ) -> RotableCycleOut:
        org_id = self.resolve_org_id(actor)
        row = self.repo.get_rotable_cycle(org_id, cycle_id, for_update=True)
        if row is None:
            raise HTTPException(status_code=404, detail="Rotable cycle not found")
        if row.status in {"closed", "cancelled"}:
            raise HTTPException(status_code=409, detail=f"Rotable cycle is '{row.status}'")
        now = _utcnow()
        row.status = "closed"
        row.closed_at = now
        if payload.notes:
            row.notes = f"{row.notes}\n{payload.notes}".strip()
        unit = self.repo.get_stock_unit(org_id, row.stock_unit_id, for_update=True)
        if unit is not None:
            unit.condition = payload.condition
            unit.is_loan = "false"
            unit.is_rental = "false"
            unit.updated_at = now
        self._commit_or_conflict(detail="Rotable cycle close conflict")
        self.repo.refresh(row)
        return RotableCycleOut.model_validate(row)

    def list_rotable_cycles(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RotableCycleOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            RotableCycleOut.model_validate(r)
            for r in self.repo.list_rotable_cycles(
                organization_id=org_id, status=status, limit=limit, offset=offset
            )
        ]

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    def _tool_event(self, org_id: str, tool_id: str, event_type: str, details: str, actor: ActorContext) -> None:
        self.repo.add_tool_history(
            ToolHistory(
                organization_id=org_id,
                tool_id=tool_id,
                event_type=event_type,
                details=details,
                performed_by=actor.username,
                created_at=_utcnow(),
            )
        )

    def create_tool(self, payload: ToolCreate, actor: ActorContext) -> ToolOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        code = payload.tool_code.strip().upper()
        if self.repo.get_tool_by_code(org_id, code) is not None:
            raise HTTPException(status_code=409, detail="Tool code already exists")
        if payload.location_id:
            self._require_location(org_id, payload.location_id)
        now = _utcnow()
        row = Tool(
            organization_id=org_id,
            tool_code=code,
            description=(payload.description or "").strip(),
            serial_number=(payload.serial_number or "").strip(),
            location_id=payload.location_id,
            status="available",
            calibration_required=_flag(payload.calibration_required),
            calibration_due_at=payload.calibration_due_at,
            calibration_status=self._calibration_status(payload.calibration_required, payload.calibration_due_at, now),
            certificate_uri=(payload.certificate_uri or "").strip(),
            created_at=now,
            updated_at=now,
        )
        self.repo.add_tool(row)
        self.repo.flush()
        self._tool_event(org_id, row.id, "created", f"code={code}", actor)
        self._commit_or_conflict(detail="Tool conflict")
        self.repo.refresh(row)
        return ToolOut.model_validate(row)

    @staticmethod
    def _calibration_status(required: bool, due_at: datetime | None, now: datetime) -> str:
        if not required:
            return "not_required"
        if due_at is None:
            return "unknown"
        if due_at < now:
            return "overdue"
        if due_at <= now + timedelta(days=30):
            return "due_soon"
        return "current"

    def update_tool(self, tool_id: str, payload: ToolUpdate, actor: ActorContext) -> ToolOut:
        org_id = self.resolve_org_id(actor)
        row = self._require_tool(org_id, tool_id, for_update=True)
        data = payload.model_dump(exclude_unset=True)
        if data.get("location_id"):
            self._require_location(org_id, str(data["location_id"]))
        for field in ("description", "serial_number", "location_id", "calibration_due_at", "certificate_uri", "status"):
            if field in data and data[field] is not None:
                setattr(row, field, data[field])
        if data.get("calibration_required") is not None:
            row.calibration_required = _flag(bool(data["calibration_required"]))
        now = _utcnow()
        row.calibration_status = self._calibration_status(
            _truthy(row.calibration_required), row.calibration_due_at, now
        )
        row.updated_at = now
        self._tool_event(org_id, row.id, "updated", ";".join(sorted(data)), actor)
        self._commit_or_conflict(detail="Tool update conflict")
        self.repo.refresh(row)
        return ToolOut.model_validate(row)

    def get_tool(self, tool_id: str, actor: ActorContext) -> ToolOut:
        org_id = self.resolve_org_id(actor)
        return ToolOut.model_validate(self._require_tool(org_id, tool_id))

    def list_tools(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        q: str | None = None,
        status: str | None = None,
        calibration_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ToolOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            ToolOut.model_validate(r)
            for r in self.repo.list_tools(
                organization_id=org_id,
                q=q,
                status=status,
                calibration_status=calibration_status,
                limit=limit,
                offset=offset,
            )
        ]

    def calibrate_tool(self, tool_id: str, payload: ToolCalibrateRequest, actor: ActorContext) -> ToolCalibrationOut:
        org_id = self.resolve_org_id(actor)
        tool = self._require_tool(org_id, tool_id, for_update=True)
        now = _utcnow()
        calibrated_at = payload.calibrated_at or now
        due_at = payload.due_at or calibrated_at + timedelta(days=payload.interval_days)
        row = ToolCalibration(
            organization_id=org_id,
            tool_id=tool.id,
            calibrated_at=calibrated_at,
            due_at=due_at,
            certificate_number=(payload.certificate_number or "").strip(),
            certificate_uri=(payload.certificate_uri or "").strip(),
            performed_by=actor.username,
            notes=(payload.notes or "").strip(),
            created_at=now,
        )
        self.repo.add_tool_calibration(row)
        tool.calibration_due_at = due_at
        tool.calibration_status = self._calibration_status(True, due_at, now)
        tool.calibration_required = "true"
        if payload.certificate_uri:
            tool.certificate_uri = payload.certificate_uri.strip()
        if tool.status == "calibration_due":
            tool.status = "available"
        tool.updated_at = now
        self._tool_event(org_id, tool.id, "calibrated", f"due={due_at.isoformat()}", actor)
        self._audit_required(
            actor,
            action="logistics.tool.calibrate",
            target_type="logistics_tool",
            target_id=tool.id,
            organization_id=org_id,
            details=f"code={tool.tool_code};due={due_at.isoformat()}",
        )
        self._commit_or_conflict(detail="Tool calibration conflict")
        self.repo.refresh(row)
        return ToolCalibrationOut.model_validate(row)

    def list_tool_calibrations(self, tool_id: str, actor: ActorContext) -> list[ToolCalibrationOut]:
        org_id = self.resolve_org_id(actor)
        self._require_tool(org_id, tool_id)
        return [
            ToolCalibrationOut.model_validate(r)
            for r in self.repo.list_tool_calibrations(organization_id=org_id, tool_id=tool_id)
        ]

    def reserve_tool(self, tool_id: str, payload: ToolReserveRequest, actor: ActorContext) -> ToolReservationOut:
        org_id = self.resolve_org_id(actor)
        tool = self._require_tool(org_id, tool_id, for_update=True)
        if tool.status not in {"available"}:
            raise HTTPException(status_code=409, detail=f"Tool is '{tool.status}' and cannot be reserved")
        row = self._reserve_tool_row(org_id, tool, payload.work_package_id, payload.tool_plan_line_id, actor)
        self._commit_or_conflict(detail="Tool reservation conflict")
        self.repo.refresh(row)
        return ToolReservationOut.model_validate(row)

    def _reserve_tool_row(
        self,
        org_id: str,
        tool: Tool,
        work_package_id: str | None,
        tool_plan_line_id: str | None,
        actor: ActorContext,
    ) -> ToolReservation:
        now = _utcnow()
        row = ToolReservation(
            organization_id=org_id,
            tool_id=tool.id,
            work_package_id=work_package_id,
            tool_plan_line_id=tool_plan_line_id,
            status="open",
            created_by=actor.username,
            created_at=now,
        )
        self.repo.add_tool_reservation(row)
        tool.status = "reserved"
        tool.updated_at = now
        self._tool_event(org_id, tool.id, "reserved", f"work_package={work_package_id or ''}", actor)
        self.repo.flush()
        return row

    def issue_tool(self, tool_id: str, payload: ToolIssueRequest, actor: ActorContext) -> ToolIssueOut:
        org_id = self.resolve_org_id(actor)
        tool = self._require_tool(org_id, tool_id, for_update=True)
        if tool.status not in {"available", "reserved"}:
            raise HTTPException(status_code=409, detail=f"Tool is '{tool.status}' and cannot be issued")
        now = _utcnow()
        if _truthy(tool.calibration_required) and tool.calibration_due_at and tool.calibration_due_at < now:
            raise HTTPException(status_code=409, detail="Tool calibration is overdue")
        row = ToolIssue(
            organization_id=org_id,
            tool_id=tool.id,
            issued_to=payload.issued_to.strip(),
            work_package_id=payload.work_package_id,
            status="issued",
            issued_at=now,
            issued_by=actor.username,
        )
        self.repo.add_tool_issue(row)
        tool.status = "issued"
        tool.updated_at = now
        for reservation in self.repo.list_tool_reservations(organization_id=org_id, tool_id=tool.id, status="open"):
            reservation.status = "issued"
        self._tool_event(org_id, tool.id, "issued", f"to={payload.issued_to}", actor)
        self._audit_required(
            actor,
            action="logistics.tool.issue",
            target_type="logistics_tool",
            target_id=tool.id,
            organization_id=org_id,
            details=f"code={tool.tool_code};to={payload.issued_to}",
        )
        self._commit_or_conflict(detail="Tool issue conflict")
        self.repo.refresh(row)
        return ToolIssueOut.model_validate(row)

    def return_tool(self, tool_id: str, actor: ActorContext) -> ToolIssueOut:
        org_id = self.resolve_org_id(actor)
        tool = self._require_tool(org_id, tool_id, for_update=True)
        issue = self.repo.get_open_tool_issue(org_id, tool.id)
        if issue is None:
            raise HTTPException(status_code=409, detail="Tool has no open issue")
        now = _utcnow()
        issue.status = "returned"
        issue.returned_at = now
        tool.status = "available"
        tool.calibration_status = self._calibration_status(
            _truthy(tool.calibration_required), tool.calibration_due_at, now
        )
        if tool.calibration_status == "overdue":
            tool.status = "calibration_due"
        tool.updated_at = now
        self._tool_event(org_id, tool.id, "returned", f"from={issue.issued_to}", actor)
        self._audit_required(
            actor,
            action="logistics.tool.return",
            target_type="logistics_tool",
            target_id=tool.id,
            organization_id=org_id,
            details=f"code={tool.tool_code}",
        )
        self._commit_or_conflict(detail="Tool return conflict")
        self.repo.refresh(issue)
        return ToolIssueOut.model_validate(issue)

    def report_lost_tool(
        self, tool_id: str, payload: LostToolReportCreate, actor: ActorContext
    ) -> LostToolReportOut:
        org_id = self.resolve_org_id(actor)
        tool = self._require_tool(org_id, tool_id, for_update=True)
        now = _utcnow()
        row = LostToolReport(
            organization_id=org_id,
            tool_id=tool.id,
            reported_by=actor.username,
            aircraft_id=payload.aircraft_id,
            description=payload.description.strip(),
            status="open",
            created_at=now,
        )
        self.repo.add_lost_tool_report(row)
        tool.status = "missing"
        tool.updated_at = now
        self._tool_event(org_id, tool.id, "lost", payload.description[:200], actor)
        self._audit_required(
            actor,
            action="logistics.tool.lost",
            target_type="logistics_tool",
            target_id=tool.id,
            organization_id=org_id,
            details=f"code={tool.tool_code};aircraft={payload.aircraft_id or ''}",
        )
        self._commit_or_conflict(detail="Lost tool report conflict")
        self.repo.refresh(row)
        return LostToolReportOut.model_validate(row)

    def list_lost_tool_reports(
        self, actor: ActorContext, *, organization_id: str | None = None, status: str | None = None, limit: int = 100
    ) -> list[LostToolReportOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            LostToolReportOut.model_validate(r)
            for r in self.repo.list_lost_tool_reports(organization_id=org_id, status=status, limit=limit)
        ]

    def list_tool_history(self, tool_id: str, actor: ActorContext, *, limit: int = 100) -> list[ToolHistoryOut]:
        org_id = self.resolve_org_id(actor)
        self._require_tool(org_id, tool_id)
        return [
            ToolHistoryOut.model_validate(r)
            for r in self.repo.list_tool_history(organization_id=org_id, tool_id=tool_id, limit=limit)
        ]

    # ------------------------------------------------------------------
    # Material requests
    # ------------------------------------------------------------------
    def _assert_mr_transition(self, current: str, target: str) -> None:
        allowed = MATERIAL_REQUEST_TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise HTTPException(status_code=409, detail=f"Cannot move material request from '{current}' to '{target}'")

    def _material_request_detail(self, org_id: str, request: MaterialRequest) -> MaterialRequestDetailOut:
        lines = self.repo.list_material_request_lines(organization_id=org_id, request_id=request.id)
        return MaterialRequestDetailOut(
            **MaterialRequestOut.model_validate(request).model_dump(),
            lines=[MaterialRequestLineOut.model_validate(line) for line in lines],
        )

    def create_material_request(
        self, payload: MaterialRequestCreate, actor: ActorContext
    ) -> MaterialRequestDetailOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        now = _utcnow()
        request = MaterialRequest(
            organization_id=org_id,
            request_number=_number("MR"),
            work_order_id=payload.work_order_id,
            work_package_id=payload.work_package_id,
            job_card_id=payload.job_card_id,
            requested_by=actor.username,
            status="requested",
            notes=(payload.notes or "").strip(),
            created_at=now,
            updated_at=now,
        )
        self.repo.add_material_request(request)
        self.repo.flush()
        for line in payload.lines:
            self._require_part(org_id, line.part_master_id)
            self.repo.add_material_request_line(
                MaterialRequestLine(
                    organization_id=org_id,
                    material_request_id=request.id,
                    part_master_id=line.part_master_id,
                    qty_requested=_dec(line.qty_requested),
                    status="requested",
                )
            )
        self._commit_or_conflict(detail="Material request conflict")
        self.repo.refresh(request)
        return self._material_request_detail(org_id, request)

    def list_material_requests(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        work_package_id: str | None = None,
        work_order_id: str | None = None,
        job_card_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MaterialRequestOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            MaterialRequestOut.model_validate(r)
            for r in self.repo.list_material_requests(
                organization_id=org_id,
                status=status,
                work_package_id=work_package_id,
                work_order_id=work_order_id,
                job_card_id=job_card_id,
                limit=limit,
                offset=offset,
            )
        ]

    def get_material_request(self, request_id: str, actor: ActorContext) -> MaterialRequestDetailOut:
        org_id = self.resolve_org_id(actor)
        request = self.repo.get_material_request(org_id, request_id)
        if request is None:
            raise HTTPException(status_code=404, detail="Material request not found")
        return self._material_request_detail(org_id, request)

    def approve_material_request(self, request_id: str, actor: ActorContext) -> MaterialRequestDetailOut:
        org_id = self.resolve_org_id(actor)
        request = self.repo.get_material_request(org_id, request_id, for_update=True)
        if request is None:
            raise HTTPException(status_code=404, detail="Material request not found")
        self._assert_mr_transition(request.status, "approved")
        now = _utcnow()
        request.status = "approved"
        request.approved_by = actor.username
        request.updated_at = now
        for line in self.repo.list_material_request_lines(organization_id=org_id, request_id=request.id):
            line.status = "approved"
        self._audit_required(
            actor,
            action="logistics.material_request.approve",
            target_type="logistics_material_request",
            target_id=request.id,
            organization_id=org_id,
            details=f"number={request.request_number}",
        )
        self._commit_or_conflict(detail="Material request approve conflict")
        self.repo.refresh(request)
        return self._material_request_detail(org_id, request)

    def reserve_material_request(self, request_id: str, actor: ActorContext) -> MaterialRequestDetailOut:
        org_id = self.resolve_org_id(actor)
        request = self.repo.get_material_request(org_id, request_id, for_update=True)
        if request is None:
            raise HTTPException(status_code=404, detail="Material request not found")
        self._assert_mr_transition(request.status, "reserved")
        now = _utcnow()
        lines = self.repo.list_material_request_lines(organization_id=org_id, request_id=request.id)
        for line in lines:
            outstanding = _dec(line.qty_requested) - _dec(line.qty_reserved) - _dec(line.qty_issued)
            if outstanding <= ZERO:
                continue
            part = self._require_part(org_id, line.part_master_id)
            available = self.repo.available_qty(org_id, part.id)
            take = outstanding if available >= outstanding else available
            if take <= ZERO:
                line.status = "shortage"
                continue
            self._reserve(
                org_id,
                part=part,
                qty=take,
                performed_by=actor.username,
                source_type="material_request",
                source_id=request.id,
                now=now,
            )
            line.qty_reserved = _dec(line.qty_reserved) + take
            line.status = "reserved" if take >= outstanding else "partial"
        request.status = "reserved"
        request.updated_at = now
        self._commit_or_conflict(detail="Material request reserve conflict")
        self.repo.refresh(request)
        return self._material_request_detail(org_id, request)

    def issue_material_request(
        self, request_id: str, payload: MaterialRequestIssueRequest, actor: ActorContext
    ) -> MaterialRequestDetailOut:
        org_id = self.resolve_org_id(actor)
        request = self.repo.get_material_request(org_id, request_id, for_update=True)
        if request is None:
            raise HTTPException(status_code=404, detail="Material request not found")
        self._assert_mr_transition(request.status, "issued")
        if payload.location_id:
            self._require_location(org_id, payload.location_id)
        now = _utcnow()
        reservations = {
            r.part_master_id: r
            for r in self.repo.list_reservations(
                organization_id=org_id, status="open", source_type="material_request", source_id=request.id
            )
        }
        lines = self.repo.list_material_request_lines(organization_id=org_id, request_id=request.id)
        for line in lines:
            outstanding = _dec(line.qty_requested) - _dec(line.qty_issued)
            if outstanding <= ZERO:
                continue
            part = self._require_part(org_id, line.part_master_id)
            reservation = reservations.get(part.id)
            from_reserved = ZERO
            location_id = payload.location_id
            if reservation is not None:
                issue_qty = outstanding if _dec(reservation.qty) >= outstanding else _dec(reservation.qty)
                from_reserved = issue_qty
                location_id = reservation.location_id or location_id
            else:
                issue_qty = outstanding
            self._withdraw(
                org_id,
                part=part,
                qty=issue_qty,
                condition="serviceable",
                performed_by=actor.username,
                movement_type="issue",
                location_id=location_id,
                from_reserved=from_reserved,
                reference_type="mr",
                reference_id=request.id,
                notes=payload.notes or f"material request {request.request_number}",
                now=now,
            )
            if reservation is not None:
                reservation.qty = _dec(reservation.qty) - issue_qty
                if _dec(reservation.qty) <= ZERO:
                    reservation.status = "issued"
                    reservation.released_at = now
            line.qty_issued = _dec(line.qty_issued) + issue_qty
            line.qty_reserved = max(_dec(line.qty_reserved) - issue_qty, ZERO)
            line.status = "issued" if _dec(line.qty_issued) >= _dec(line.qty_requested) else "partial"
        request.status = "issued"
        request.updated_at = now
        self._audit_required(
            actor,
            action="logistics.material_request.issue",
            target_type="logistics_material_request",
            target_id=request.id,
            organization_id=org_id,
            details=f"number={request.request_number};lines={len(lines)}",
        )
        self._commit_or_conflict(detail="Material request issue conflict")
        self.repo.refresh(request)
        return self._material_request_detail(org_id, request)

    def return_material_request(
        self, request_id: str, payload: MaterialRequestReturnRequest, actor: ActorContext
    ) -> MaterialRequestDetailOut:
        org_id = self.resolve_org_id(actor)
        request = self.repo.get_material_request(org_id, request_id, for_update=True)
        if request is None:
            raise HTTPException(status_code=404, detail="Material request not found")
        self._assert_mr_transition(request.status, "returned")
        location = self._require_location(org_id, payload.location_id)
        now = _utcnow()
        for entry in payload.lines:
            line = self.repo.get_material_request_line(org_id, entry.line_id)
            if line is None or line.material_request_id != request.id:
                raise HTTPException(status_code=404, detail="Material request line not found")
            returnable = _dec(line.qty_issued) - _dec(line.qty_returned)
            qty = _dec(entry.qty)
            if qty > returnable:
                raise HTTPException(status_code=409, detail="Return quantity exceeds issued quantity")
            part = self._require_part(org_id, line.part_master_id)
            balance = self.repo.get_or_create_balance(org_id, part.id, location.id, entry.condition, now=now)
            balance.qty_on_hand = _dec(balance.qty_on_hand) + qty
            balance.updated_at = now
            self._movement(
                org_id,
                movement_type="return",
                part_master_id=part.id,
                qty=qty,
                condition=entry.condition,
                performed_by=actor.username,
                to_location_id=location.id,
                reference_type="mr",
                reference_id=request.id,
                notes=payload.notes or f"return to {location.location_code}",
                now=now,
            )
            line.qty_returned = _dec(line.qty_returned) + qty
            line.status = "returned"
        request.status = "returned"
        request.updated_at = now
        self._audit_required(
            actor,
            action="logistics.material_request.return",
            target_type="logistics_material_request",
            target_id=request.id,
            organization_id=org_id,
            details=f"number={request.request_number}",
        )
        self._commit_or_conflict(detail="Material request return conflict")
        self.repo.refresh(request)
        return self._material_request_detail(org_id, request)

    def cancel_material_request(self, request_id: str, actor: ActorContext) -> MaterialRequestDetailOut:
        org_id = self.resolve_org_id(actor)
        request = self.repo.get_material_request(org_id, request_id, for_update=True)
        if request is None:
            raise HTTPException(status_code=404, detail="Material request not found")
        self._assert_mr_transition(request.status, "cancelled")
        now = _utcnow()
        for reservation in self.repo.list_reservations(
            organization_id=org_id, status="open", source_type="material_request", source_id=request.id
        ):
            self._release(org_id, reservation, performed_by=actor.username, now=now)
        for line in self.repo.list_material_request_lines(organization_id=org_id, request_id=request.id):
            line.qty_reserved = ZERO
            line.status = "cancelled"
        request.status = "cancelled"
        request.updated_at = now
        self._commit_or_conflict(detail="Material request cancel conflict")
        self.repo.refresh(request)
        return self._material_request_detail(org_id, request)

    # ------------------------------------------------------------------
    # Vendors
    # ------------------------------------------------------------------
    def create_vendor(self, payload: VendorCreate, actor: ActorContext) -> VendorOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        code = payload.code.strip().upper()
        if self.repo.get_vendor_by_code(org_id, code) is not None:
            raise HTTPException(status_code=409, detail="Vendor code already exists")
        now = _utcnow()
        row = Vendor(
            organization_id=org_id,
            code=code,
            name=payload.name.strip(),
            vendor_type=payload.vendor_type,
            certificates=(payload.certificates or "").strip(),
            approvals=(payload.approvals or "").strip(),
            contacts=(payload.contacts or "").strip(),
            rating=payload.rating,
            lead_time_days=payload.lead_time_days,
            performance_score=payload.performance_score,
            warranty_terms=(payload.warranty_terms or "").strip(),
            repair_capability=_flag(payload.repair_capability),
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_vendor(row)
        self._commit_or_conflict(detail="Vendor conflict")
        self.repo.refresh(row)
        return VendorOut.model_validate(row)

    def update_vendor(self, vendor_id: str, payload: VendorUpdate, actor: ActorContext) -> VendorOut:
        org_id = self.resolve_org_id(actor)
        row = self._require_vendor(org_id, vendor_id)
        data = payload.model_dump(exclude_unset=True, exclude_none=True)
        for field in (
            "name",
            "vendor_type",
            "certificates",
            "approvals",
            "contacts",
            "rating",
            "lead_time_days",
            "performance_score",
            "warranty_terms",
            "status",
        ):
            if field in data:
                setattr(row, field, data[field])
        if "repair_capability" in data:
            row.repair_capability = _flag(bool(data["repair_capability"]))
        row.updated_at = _utcnow()
        self._commit_or_conflict(detail="Vendor update conflict")
        self.repo.refresh(row)
        return VendorOut.model_validate(row)

    def get_vendor(self, vendor_id: str, actor: ActorContext) -> VendorOut:
        org_id = self.resolve_org_id(actor)
        return VendorOut.model_validate(self._require_vendor(org_id, vendor_id))

    def list_vendors(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        q: str | None = None,
        vendor_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[VendorOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            VendorOut.model_validate(r)
            for r in self.repo.list_vendors(
                organization_id=org_id, q=q, vendor_type=vendor_type, status=status, limit=limit, offset=offset
            )
        ]

    # ------------------------------------------------------------------
    # Purchasing chain
    # ------------------------------------------------------------------
    def _purchase_request_detail(self, org_id: str, request: PurchaseRequest) -> PurchaseRequestDetailOut:
        lines = self.repo.list_purchase_request_lines(organization_id=org_id, request_id=request.id)
        return PurchaseRequestDetailOut(
            **PurchaseRequestOut.model_validate(request).model_dump(),
            lines=[PurchaseRequestLineOut.model_validate(line) for line in lines],
        )

    def create_purchase_request(
        self, payload: PurchaseRequestCreate, actor: ActorContext
    ) -> PurchaseRequestDetailOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        now = _utcnow()
        request = PurchaseRequest(
            organization_id=org_id,
            request_number=_number("PR"),
            status="draft",
            requested_by=actor.username,
            work_package_id=payload.work_package_id,
            notes=(payload.notes or "").strip(),
            created_at=now,
            updated_at=now,
        )
        self.repo.add_purchase_request(request)
        self.repo.flush()
        for line in payload.lines:
            self._require_part(org_id, line.part_master_id)
            self.repo.add_purchase_request_line(
                PurchaseRequestLine(
                    organization_id=org_id,
                    purchase_request_id=request.id,
                    part_master_id=line.part_master_id,
                    qty=_dec(line.qty),
                    needed_by=line.needed_by,
                    status="open",
                )
            )
        self._commit_or_conflict(detail="Purchase request conflict")
        self.repo.refresh(request)
        return self._purchase_request_detail(org_id, request)

    def list_purchase_requests(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PurchaseRequestOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            PurchaseRequestOut.model_validate(r)
            for r in self.repo.list_purchase_requests(
                organization_id=org_id, status=status, limit=limit, offset=offset
            )
        ]

    def get_purchase_request(self, request_id: str, actor: ActorContext) -> PurchaseRequestDetailOut:
        org_id = self.resolve_org_id(actor)
        request = self.repo.get_purchase_request(org_id, request_id)
        if request is None:
            raise HTTPException(status_code=404, detail="Purchase request not found")
        return self._purchase_request_detail(org_id, request)

    def approve_purchase_request(self, request_id: str, actor: ActorContext) -> PurchaseRequestDetailOut:
        org_id = self.resolve_org_id(actor)
        request = self.repo.get_purchase_request(org_id, request_id, for_update=True)
        if request is None:
            raise HTTPException(status_code=404, detail="Purchase request not found")
        if request.status != "draft":
            raise HTTPException(status_code=409, detail=f"Cannot approve purchase request in '{request.status}'")
        request.status = "approved"
        request.approved_by = actor.username
        request.updated_at = _utcnow()
        self._audit_required(
            actor,
            action="logistics.purchase_request.approve",
            target_type="logistics_purchase_request",
            target_id=request.id,
            organization_id=org_id,
            details=f"number={request.request_number}",
        )
        self._commit_or_conflict(detail="Purchase request approve conflict")
        self.repo.refresh(request)
        return self._purchase_request_detail(org_id, request)

    def create_rfq(self, request_id: str, actor: ActorContext) -> RfqDetailOut:
        org_id = self.resolve_org_id(actor)
        request = self.repo.get_purchase_request(org_id, request_id, for_update=True)
        if request is None:
            raise HTTPException(status_code=404, detail="Purchase request not found")
        if request.status != "approved":
            raise HTTPException(status_code=409, detail="Purchase request must be approved before RFQ")
        now = _utcnow()
        rfq = Rfq(
            organization_id=org_id,
            rfq_number=_number("RFQ"),
            purchase_request_id=request.id,
            status="open",
            created_at=now,
        )
        self.repo.add_rfq(rfq)
        request.status = "rfq"
        request.updated_at = now
        self._commit_or_conflict(detail="RFQ conflict")
        self.repo.refresh(rfq)
        return RfqDetailOut(**RfqOut.model_validate(rfq).model_dump(), quotes=[])

    def list_rfqs(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RfqOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            RfqOut.model_validate(r)
            for r in self.repo.list_rfqs(organization_id=org_id, status=status, limit=limit, offset=offset)
        ]

    def get_rfq(self, rfq_id: str, actor: ActorContext) -> RfqDetailOut:
        org_id = self.resolve_org_id(actor)
        rfq = self.repo.get_rfq(org_id, rfq_id)
        if rfq is None:
            raise HTTPException(status_code=404, detail="RFQ not found")
        quotes = self.repo.list_quotes(organization_id=org_id, rfq_id=rfq.id)
        return RfqDetailOut(
            **RfqOut.model_validate(rfq).model_dump(),
            quotes=[RfqQuoteOut.model_validate(q) for q in quotes],
        )

    def add_quote(self, rfq_id: str, payload: RfqQuoteCreate, actor: ActorContext) -> RfqQuoteOut:
        org_id = self.resolve_org_id(actor)
        rfq = self.repo.get_rfq(org_id, rfq_id)
        if rfq is None:
            raise HTTPException(status_code=404, detail="RFQ not found")
        if rfq.status != "open":
            raise HTTPException(status_code=409, detail=f"RFQ is '{rfq.status}'")
        vendor = self._require_vendor(org_id, payload.vendor_id)
        row = RfqQuote(
            organization_id=org_id,
            rfq_id=rfq.id,
            vendor_id=vendor.id,
            currency=payload.currency.strip().upper(),
            unit_price=_dec(payload.unit_price),
            lead_time_days=payload.lead_time_days,
            selected="false",
            notes=(payload.notes or "").strip(),
            created_at=_utcnow(),
        )
        self.repo.add_quote(row)
        self._commit_or_conflict(detail="Quote conflict")
        self.repo.refresh(row)
        return RfqQuoteOut.model_validate(row)

    def select_quote(self, rfq_id: str, quote_id: str, actor: ActorContext) -> RfqDetailOut:
        org_id = self.resolve_org_id(actor)
        rfq = self.repo.get_rfq(org_id, rfq_id, for_update=True)
        if rfq is None:
            raise HTTPException(status_code=404, detail="RFQ not found")
        quotes = self.repo.list_quotes(organization_id=org_id, rfq_id=rfq.id)
        if not any(q.id == quote_id for q in quotes):
            raise HTTPException(status_code=404, detail="Quote not found on this RFQ")
        for quote in quotes:
            quote.selected = _flag(quote.id == quote_id)
        self._audit_required(
            actor,
            action="logistics.rfq.select_vendor",
            target_type="logistics_rfq",
            target_id=rfq.id,
            organization_id=org_id,
            details=f"quote={quote_id}",
        )
        self._commit_or_conflict(detail="Quote selection conflict")
        return RfqDetailOut(
            **RfqOut.model_validate(rfq).model_dump(),
            quotes=[RfqQuoteOut.model_validate(q) for q in quotes],
        )

    def _purchase_order_detail(self, org_id: str, po: PurchaseOrder) -> PurchaseOrderDetailOut:
        lines = self.repo.list_purchase_order_lines(organization_id=org_id, po_id=po.id)
        return PurchaseOrderDetailOut(
            **PurchaseOrderOut.model_validate(po).model_dump(),
            lines=[PurchaseOrderLineOut.model_validate(line) for line in lines],
        )

    def create_purchase_order_from_rfq(
        self, rfq_id: str, payload: PurchaseOrderCreateFromRfq, actor: ActorContext
    ) -> PurchaseOrderDetailOut:
        org_id = self.resolve_org_id(actor)
        rfq = self.repo.get_rfq(org_id, rfq_id, for_update=True)
        if rfq is None:
            raise HTTPException(status_code=404, detail="RFQ not found")
        if rfq.status != "open":
            raise HTTPException(status_code=409, detail=f"RFQ is '{rfq.status}'")
        quotes = self.repo.list_quotes(organization_id=org_id, rfq_id=rfq.id)
        selected = next((q for q in quotes if _truthy(q.selected)), None)
        if selected is None:
            raise HTTPException(status_code=409, detail="Select a vendor quote before creating the purchase order")
        request = self.repo.get_purchase_request(org_id, rfq.purchase_request_id, for_update=True)
        if request is None:
            raise HTTPException(status_code=404, detail="Purchase request not found")
        pr_lines = self.repo.list_purchase_request_lines(organization_id=org_id, request_id=request.id)
        if not pr_lines:
            raise HTTPException(status_code=409, detail="Purchase request has no lines")
        vendor = self._require_vendor(org_id, selected.vendor_id)
        now = _utcnow()
        expected = payload.expected_delivery or now + timedelta(days=int(selected.lead_time_days or 14))
        po = PurchaseOrder(
            organization_id=org_id,
            po_number=_number("PO"),
            vendor_id=vendor.id,
            purchase_request_id=request.id,
            currency=selected.currency,
            tax_amount=_dec(payload.tax_amount),
            shipping_amount=_dec(payload.shipping_amount),
            expected_delivery=expected,
            status="open",
            warranty_terms=(payload.warranty_terms or vendor.warranty_terms or "").strip(),
            notes=(payload.notes or "").strip(),
            created_by=actor.username,
            created_at=now,
            updated_at=now,
        )
        self.repo.add_purchase_order(po)
        self.repo.flush()
        for line in pr_lines:
            self.repo.add_purchase_order_line(
                PurchaseOrderLine(
                    organization_id=org_id,
                    purchase_order_id=po.id,
                    part_master_id=line.part_master_id,
                    qty_ordered=_dec(line.qty),
                    qty_received=ZERO,
                    qty_backordered=_dec(line.qty),
                    unit_price=_dec(selected.unit_price),
                    status="open",
                )
            )
            line.status = "ordered"
        rfq.status = "closed"
        request.status = "po_created"
        request.updated_at = now
        self._audit_required(
            actor,
            action="logistics.purchase_order.create",
            target_type="logistics_purchase_order",
            target_id=po.id,
            organization_id=org_id,
            details=f"number={po.po_number};vendor={vendor.code}",
        )
        self._commit_or_conflict(detail="Purchase order conflict")
        self.repo.refresh(po)
        self._sync_po_workflow(actor, org_id=org_id, po_id=po.id, from_state="open", to_state="open", comment="created")
        return self._purchase_order_detail(org_id, po)

    def list_purchase_orders(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        vendor_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PurchaseOrderOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            PurchaseOrderOut.model_validate(r)
            for r in self.repo.list_purchase_orders(
                organization_id=org_id, status=status, vendor_id=vendor_id, limit=limit, offset=offset
            )
        ]

    def get_purchase_order(self, po_id: str, actor: ActorContext) -> PurchaseOrderDetailOut:
        org_id = self.resolve_org_id(actor)
        po = self.repo.get_purchase_order(org_id, po_id)
        if po is None:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        return self._purchase_order_detail(org_id, po)

    def _receipt_detail(self, org_id: str, receipt: Receipt) -> ReceiptDetailOut:
        lines = self.repo.list_receipt_lines(organization_id=org_id, receipt_id=receipt.id)
        return ReceiptDetailOut(
            **ReceiptOut.model_validate(receipt).model_dump(),
            lines=[ReceiptLineOut.model_validate(line) for line in lines],
        )

    def get_receipt(self, receipt_id: str, actor: ActorContext) -> ReceiptDetailOut:
        org_id = self.resolve_org_id(actor)
        receipt = self.repo.get_receipt(org_id, receipt_id)
        if receipt is None:
            raise HTTPException(status_code=404, detail="Receipt not found")
        return self._receipt_detail(org_id, receipt)

    def receive_purchase_order(
        self, po_id: str, payload: ReceiptCreate, actor: ActorContext
    ) -> ReceiptDetailOut:
        """Record a full or partial receipt against a purchase order (goods-in only)."""
        org_id = self.resolve_org_id(actor, payload.organization_id)
        po = self.repo.get_purchase_order(org_id, po_id, for_update=True)
        if po is None:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        if po.status in {"closed", "cancelled"}:
            raise HTTPException(status_code=409, detail=f"Purchase order is '{po.status}'")
        location = None
        if payload.location_id:
            location = self._require_location(org_id, payload.location_id)
        else:
            location = self.repo.first_location_of_type(org_id, "receiving")
        if location is None:
            raise HTTPException(status_code=409, detail="No receiving location configured")
        po_lines = {line.id: line for line in self.repo.list_purchase_order_lines(organization_id=org_id, po_id=po.id)}
        now = _utcnow()
        receipt = Receipt(
            organization_id=org_id,
            receipt_number=_number("RCPT"),
            purchase_order_id=po.id,
            shipment_id=payload.shipment_id,
            location_id=location.id,
            status="receiving",
            received_by=actor.username,
            created_at=now,
        )
        self.repo.add_receipt(receipt)
        self.repo.flush()
        for line in payload.lines:
            po_line = po_lines.get(line.purchase_order_line_id or "")
            if po_line is None and line.part_master_id:
                po_line = next((pl for pl in po_lines.values() if pl.part_master_id == line.part_master_id), None)
            if po_line is None:
                raise HTTPException(status_code=404, detail="Purchase order line not found for receipt line")
            qty = _dec(line.qty)
            outstanding = _dec(po_line.qty_ordered) - _dec(po_line.qty_received)
            if qty > outstanding:
                raise HTTPException(
                    status_code=409,
                    detail=f"Receipt quantity {qty} exceeds outstanding {outstanding} on purchase order line",
                )
            po_line.qty_received = _dec(po_line.qty_received) + qty
            po_line.qty_backordered = _dec(po_line.qty_ordered) - _dec(po_line.qty_received)
            po_line.status = "received" if _dec(po_line.qty_backordered) <= ZERO else "partial"
            self.repo.add_receipt_line(
                ReceiptLine(
                    organization_id=org_id,
                    receipt_id=receipt.id,
                    purchase_order_line_id=po_line.id,
                    part_master_id=po_line.part_master_id,
                    qty=qty,
                    serial_number=(line.serial_number or "").strip(),
                    batch_number=(line.batch_number or "").strip(),
                    lot_number=(line.lot_number or "").strip(),
                    expires_at=line.expires_at,
                    inspection_status="pending",
                )
            )
        remaining = [line for line in po_lines.values() if _dec(line.qty_backordered) > ZERO]
        previous = po.status
        po.status = "partial" if remaining else "received"
        po.updated_at = now
        receipt.status = "inspection"
        if previous != po.status:
            from ..platform.workflow_bridge import PO_WORKFLOW_CODE, WorkflowBridge

            bridge = WorkflowBridge(self.db)
            bridge.ensure_purchase_order_definition(org_id)
            bridge.assert_transition(org_id, PO_WORKFLOW_CODE, previous, po.status)
        self._audit_required(
            actor,
            action="logistics.purchase_order.receive",
            target_type="logistics_receipt",
            target_id=receipt.id,
            organization_id=org_id,
            details=f"po={po.po_number};receipt={receipt.receipt_number};lines={len(payload.lines)}",
        )
        self._commit_or_conflict(detail="Receipt conflict")
        self.repo.refresh(receipt)
        if previous != po.status:
            self._sync_po_workflow(
                actor, org_id=org_id, po_id=po.id, from_state=previous, to_state=po.status, comment="receive"
            )
        return self._receipt_detail(org_id, receipt)

    def inspect_receipt(
        self, receipt_id: str, payload: ReceiptInspectRequest, actor: ActorContext
    ) -> ReceiptDetailOut:
        org_id = self.resolve_org_id(actor)
        receipt = self.repo.get_receipt(org_id, receipt_id, for_update=True)
        if receipt is None:
            raise HTTPException(status_code=404, detail="Receipt not found")
        if receipt.status not in {"receiving", "inspection"}:
            raise HTTPException(status_code=409, detail=f"Receipt is '{receipt.status}'")
        lines = {line.id: line for line in self.repo.list_receipt_lines(organization_id=org_id, receipt_id=receipt.id)}
        for entry in payload.lines:
            line = lines.get(entry.line_id)
            if line is None:
                raise HTTPException(status_code=404, detail="Receipt line not found")
            line.inspection_status = "accepted" if entry.accept else "rejected"
        receipt.status = "inspection"
        self._audit_required(
            actor,
            action="logistics.receipt.inspect",
            target_type="logistics_receipt",
            target_id=receipt.id,
            organization_id=org_id,
            details=f"number={receipt.receipt_number};lines={len(payload.lines)}",
        )
        self._commit_or_conflict(detail="Receipt inspection conflict")
        self.repo.refresh(receipt)
        return self._receipt_detail(org_id, receipt)

    def putaway_receipt(
        self, receipt_id: str, payload: ReceiptPutawayRequest, actor: ActorContext
    ) -> ReceiptDetailOut:
        """Move inspected receipt lines into stock; rejected lines go to quarantine."""
        org_id = self.resolve_org_id(actor)
        receipt = self.repo.get_receipt(org_id, receipt_id, for_update=True)
        if receipt is None:
            raise HTTPException(status_code=404, detail="Receipt not found")
        if receipt.status == "closed":
            raise HTTPException(status_code=409, detail="Receipt already put away")
        lines = self.repo.list_receipt_lines(organization_id=org_id, receipt_id=receipt.id)
        if not lines:
            raise HTTPException(status_code=409, detail="Receipt has no lines")
        if any(line.inspection_status == "pending" for line in lines):
            raise HTTPException(status_code=409, detail="All receipt lines must be inspected before putaway")

        if payload.location_id:
            target = self._require_location(org_id, payload.location_id)
        else:
            target = self.repo.first_location_of_type(org_id, "general")
        if target is None:
            raise HTTPException(status_code=409, detail="No putaway location configured")
        quarantine = None
        if payload.quarantine_location_id:
            quarantine = self._require_location(org_id, payload.quarantine_location_id)
        elif any(line.inspection_status == "rejected" for line in lines):
            quarantine = self.repo.first_location_of_type(org_id, "quarantine")
            if quarantine is None:
                raise HTTPException(status_code=409, detail="No quarantine location configured for rejected lines")

        now = _utcnow()
        for line in lines:
            part = self._require_part(org_id, line.part_master_id)
            accepted = line.inspection_status == "accepted"
            location = target if accepted else quarantine
            if location is None:
                raise HTTPException(status_code=409, detail="No destination location for receipt line")
            self._receive_into_stock(
                org_id,
                part=part,
                location=location,
                qty=_dec(line.qty),
                condition="serviceable" if accepted else "quarantine",
                performed_by=actor.username,
                serial_number=line.serial_number,
                batch_number=line.batch_number,
                lot_number=line.lot_number,
                expires_at=line.expires_at,
                reference_type="po",
                reference_id=receipt.purchase_order_id or receipt.id,
                notes=payload.notes or f"putaway {receipt.receipt_number}",
                now=now,
            )
        receipt.status = "closed"
        self._audit_required(
            actor,
            action="logistics.receipt.putaway",
            target_type="logistics_receipt",
            target_id=receipt.id,
            organization_id=org_id,
            details=f"number={receipt.receipt_number};location={target.location_code};lines={len(lines)}",
        )
        self._commit_or_conflict(detail="Putaway conflict")
        self.repo.refresh(receipt)
        return self._receipt_detail(org_id, receipt)

    def list_receipts(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        purchase_order_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ReceiptOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            ReceiptOut.model_validate(r)
            for r in self.repo.list_receipts(
                organization_id=org_id,
                status=status,
                purchase_order_id=purchase_order_id,
                limit=limit,
                offset=offset,
            )
        ]

    def create_vendor_invoice(
        self, po_id: str, payload: VendorInvoiceCreate, actor: ActorContext
    ) -> VendorInvoiceOut:
        org_id = self.resolve_org_id(actor)
        po = self.repo.get_purchase_order(org_id, po_id)
        if po is None:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        row = VendorInvoice(
            organization_id=org_id,
            invoice_number=payload.invoice_number.strip().upper(),
            purchase_order_id=po.id,
            vendor_id=po.vendor_id,
            amount=_dec(payload.amount),
            currency=payload.currency.strip().upper(),
            status="open",
            created_at=_utcnow(),
        )
        self.repo.add_vendor_invoice(row)
        self._audit_required(
            actor,
            action="logistics.vendor_invoice.create",
            target_type="logistics_vendor_invoice",
            target_id=row.id,
            organization_id=org_id,
            details=f"po={po.po_number};invoice={row.invoice_number}",
        )
        self._commit_or_conflict(detail="Vendor invoice conflict")
        self.repo.refresh(row)
        return VendorInvoiceOut.model_validate(row)

    def list_vendor_invoices(
        self, actor: ActorContext, *, organization_id: str | None = None, purchase_order_id: str | None = None
    ) -> list[VendorInvoiceOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            VendorInvoiceOut.model_validate(r)
            for r in self.repo.list_vendor_invoices(
                organization_id=org_id, purchase_order_id=purchase_order_id
            )
        ]

    def close_purchase_order(self, po_id: str, actor: ActorContext) -> PurchaseOrderDetailOut:
        org_id = self.resolve_org_id(actor)
        po = self.repo.get_purchase_order(org_id, po_id, for_update=True)
        if po is None:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        previous = po.status
        from ..platform.workflow_bridge import PO_WORKFLOW_CODE, WorkflowBridge

        bridge = WorkflowBridge(self.db)
        bridge.ensure_purchase_order_definition(org_id)
        bridge.assert_transition(org_id, PO_WORKFLOW_CODE, previous, "closed")
        now = _utcnow()
        po.status = "closed"
        po.closed_at = now
        po.updated_at = now
        for line in self.repo.list_purchase_order_lines(organization_id=org_id, po_id=po.id):
            if line.status != "received":
                line.status = "closed"
        self._audit_required(
            actor,
            action="logistics.purchase_order.close",
            target_type="logistics_purchase_order",
            target_id=po.id,
            organization_id=org_id,
            details=f"number={po.po_number}",
        )
        self._commit_or_conflict(detail="Purchase order close conflict")
        self.repo.refresh(po)
        self._sync_po_workflow(
            actor, org_id=org_id, po_id=po.id, from_state=previous, to_state="closed", comment="close"
        )
        return self._purchase_order_detail(org_id, po)

    def _sync_po_workflow(
        self,
        actor: ActorContext,
        *,
        org_id: str,
        po_id: str,
        from_state: str,
        to_state: str,
        comment: str = "",
    ) -> None:
        """Best-effort dual-write of PO status onto the platform workflow instance."""
        from ..platform.workflow_bridge import PO_WORKFLOW_CODE, WorkflowBridge
        from ..shared import ActorContext as SharedActor

        bridge = WorkflowBridge(self.db)
        bridge.ensure_purchase_order_definition(org_id)
        shared = SharedActor(
            username=actor.username,
            role=actor.role,
            organization_id=actor.organization_id or org_id,
            site_id=actor.site_id or "",
        )
        bridge.sync_instance(
            shared,
            organization_id=org_id,
            definition_code=PO_WORKFLOW_CODE,
            entity_type="logistics_purchase_order",
            entity_id=po_id,
            to_state=to_state,
            comment=comment or f"{from_state}->{to_state}",
        )

    # ------------------------------------------------------------------
    # Shipments
    # ------------------------------------------------------------------
    def create_shipment(self, payload: ShipmentCreate, actor: ActorContext) -> ShipmentOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        row = Shipment(
            organization_id=org_id,
            shipment_number=_number("SHP"),
            direction=payload.direction,
            courier=(payload.courier or "").strip(),
            tracking_number=(payload.tracking_number or "").strip(),
            packing_list=(payload.packing_list or "").strip(),
            is_export=_flag(payload.is_export),
            is_import=_flag(payload.is_import),
            is_dangerous_goods=_flag(payload.is_dangerous_goods),
            purchase_order_id=payload.purchase_order_id,
            transfer_id=payload.transfer_id,
            status="in_transit",
            created_at=_utcnow(),
        )
        self.repo.add_shipment(row)
        self._commit_or_conflict(detail="Shipment conflict")
        self.repo.refresh(row)
        return ShipmentOut.model_validate(row)

    def list_shipments(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        direction: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ShipmentOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            ShipmentOut.model_validate(r)
            for r in self.repo.list_shipments(
                organization_id=org_id, direction=direction, status=status, limit=limit, offset=offset
            )
        ]

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------
    def scan(self, payload: ScanRequest, actor: ActorContext) -> ScanOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        value = payload.value.strip()
        identifier = self.repo.get_identifier(org_id, value, identifier_type=payload.identifier_type)
        if identifier is None:
            part = self.repo.get_part_by_number(org_id, value.upper())
            if part is not None:
                return self._scan_part(org_id, part, value, payload.identifier_type or "barcode")
            tool = self.repo.get_tool_by_code(org_id, value.upper())
            if tool is not None:
                return ScanOut(
                    value=value,
                    identifier_type=payload.identifier_type or "barcode",
                    resolved=True,
                    target_type="tool",
                    target_id=tool.id,
                    title=tool.tool_code,
                    subtitle=tool.description or "",
                    tool=ToolOut.model_validate(tool),
                )
            return ScanOut(
                value=value,
                identifier_type=payload.identifier_type or "barcode",
                resolved=False,
                target_type="unknown",
                target_id="",
                title="Unknown identifier",
                subtitle="No part, stock unit or tool matches this code",
            )

        if identifier.tool_id:
            tool = self.repo.get_tool(org_id, identifier.tool_id)
            if tool is not None:
                return ScanOut(
                    value=value,
                    identifier_type=identifier.identifier_type,
                    resolved=True,
                    target_type="tool",
                    target_id=tool.id,
                    title=tool.tool_code,
                    subtitle=tool.description or "",
                    tool=ToolOut.model_validate(tool),
                )
        if identifier.stock_unit_id:
            unit = self.repo.get_stock_unit(org_id, identifier.stock_unit_id)
            if unit is not None:
                part = self.repo.get_part(org_id, unit.part_master_id)
                return ScanOut(
                    value=value,
                    identifier_type=identifier.identifier_type,
                    resolved=True,
                    target_type="stock_unit",
                    target_id=unit.id,
                    title=unit.serial_number or unit.lot_number or unit.batch_number or unit.id,
                    subtitle=part.oem_part_number if part else "",
                    part=PartMasterOut.model_validate(part) if part else None,
                    stock_unit=StockUnitOut.model_validate(unit),
                )
        if identifier.part_master_id:
            part = self.repo.get_part(org_id, identifier.part_master_id)
            if part is not None:
                return self._scan_part(org_id, part, value, identifier.identifier_type)
        return ScanOut(
            value=value,
            identifier_type=identifier.identifier_type,
            resolved=False,
            target_type="unknown",
            target_id="",
            title="Identifier target missing",
            subtitle="Identifier is registered but its target no longer exists",
        )

    def _scan_part(self, org_id: str, part: PartMaster, value: str, identifier_type: str) -> ScanOut:
        rows = self.repo.list_balances_detailed(organization_id=org_id, part_master_id=part.id, limit=50)
        return ScanOut(
            value=value,
            identifier_type=identifier_type,
            resolved=True,
            target_type="part",
            target_id=part.id,
            title=part.oem_part_number,
            subtitle=part.description or "",
            part=PartMasterOut.model_validate(part),
            balances=[self._balance_detail(balance, p, location) for balance, p, location in rows],
        )

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    def dashboard(self, actor: ActorContext, *, organization_id: str | None = None) -> DashboardOut:
        org_id = self.resolve_org_id(actor, organization_id)
        now = _utcnow()
        soon = now + timedelta(days=30)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        on_hand, reserved = self.repo.sum_stock(org_id)
        return DashboardOut(
            organization_id=org_id,
            generated_at=now,
            warehouses=self.repo.count_warehouses(org_id),
            locations=self.repo.count_locations(org_id),
            parts=self.repo.count_parts(org_id),
            stock_lines=self.repo.count_stock_lines(org_id),
            total_on_hand=on_hand,
            total_reserved=reserved,
            low_stock_parts=self.repo.count_low_stock_parts(org_id),
            expiring_lots_30d=self.repo.count_expiring_units(org_id, before=soon, after=now),
            expired_lots=self.repo.count_expiring_units(org_id, before=now),
            quarantine_lines=self.repo.count_quarantine_lines(org_id),
            open_reservations=self.repo.count_reservations(org_id, status="open"),
            movements_today=self.repo.count_movements(org_id, since=day_start),
            open_material_requests=self.repo.count_material_requests(
                org_id, statuses=("requested", "approved", "reserved")
            ),
            open_purchase_requests=self.repo.count_purchase_requests(org_id, statuses=("draft", "approved", "rfq")),
            open_purchase_orders=self.repo.count_purchase_orders(org_id, statuses=("open", "partial")),
            shipments_in_transit=self.repo.count_shipments(org_id, status="in_transit"),
            open_rotable_cycles=self.repo.count_open_rotable_cycles(org_id),
            tools_total=self.repo.count_tools(org_id),
            tools_issued=self.repo.count_tools(org_id, status="issued"),
            tools_calibration_due_30d=self.repo.count_tools_calibration_due(org_id, before=soon),
            tools_missing=self.repo.count_tools(org_id, status="missing"),
            open_lost_tool_reports=self.repo.count_lost_tool_reports(org_id, status="open"),
        )

    def list_shortages(self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100) -> ShortagesOut:
        org_id = self.resolve_org_id(actor, organization_id)
        items: list[ShortageItemOut] = []
        for part, available in self.repo.list_shortage_parts(org_id, limit=limit):
            status = "no_stock" if available <= ZERO else "low_stock"
            items.append(
                ShortageItemOut(
                    part_master_id=part.id,
                    oem_part_number=part.oem_part_number,
                    description=part.description or "",
                    part_class=part.part_class,
                    qty_available=available,
                    reorder_point=part.reorder_point,
                    min_stock=part.min_stock,
                    status=status,
                )
            )
        return ShortagesOut(organization_id=org_id, items=items)

    # ------------------------------------------------------------------
    # Planning integration
    # ------------------------------------------------------------------
    def run_material_planning(
        self,
        organization_id: str,
        work_package_id: str | None,
        parts_plan_lines: list[dict[str, object]],
        *,
        username: str = "system",
        actor: ActorContext | None = None,
        auto_purchase_request: bool = True,
    ) -> MaterialPlanningResult:
        """Reserve stock for planned parts, flagging shortages and raising a draft PR.

        `parts_plan_lines` entries carry `id`, `part_number` and `qty_required`; the
        caller (planning) applies the returned updates to its own plan lines.
        """
        now = _utcnow()
        results: list[MaterialPlanningLineResult] = []
        purchase_request: PurchaseRequest | None = None
        reserved = shortage = purchase_required = 0

        for raw in parts_plan_lines:
            line_id = str(raw.get("id") or "")
            part_number = str(raw.get("part_number") or "").strip()
            qty_required = _dec(raw.get("qty_required") or 0)
            if qty_required <= ZERO:
                qty_required = Decimal("1")
            if not part_number:
                shortage += 1
                results.append(
                    MaterialPlanningLineResult(
                        parts_plan_line_id=line_id,
                        part_number="",
                        qty_required=qty_required,
                        qty_available=ZERO,
                        qty_reserved=ZERO,
                        status="shortage",
                        message="Plan line has no part number",
                    )
                )
                continue

            part = self.repo.get_part_by_number(organization_id, part_number.upper())
            if part is None:
                purchase_required += 1
                results.append(
                    MaterialPlanningLineResult(
                        parts_plan_line_id=line_id,
                        part_number=part_number,
                        qty_required=qty_required,
                        qty_available=ZERO,
                        qty_reserved=ZERO,
                        status="purchase_required",
                        message="Part is not in the part master; purchasing required",
                    )
                )
                continue

            available = self.repo.available_qty(organization_id, part.id)
            reservation_id: str | None = None
            qty_reserved = ZERO
            if available >= qty_required:
                try:
                    reservation = self._reserve(
                        organization_id,
                        part=part,
                        qty=qty_required,
                        performed_by=username,
                        source_type="work_package",
                        source_id=work_package_id or "",
                        parts_plan_line_id=line_id or None,
                        now=now,
                    )
                    reservation_id = reservation.id
                    qty_reserved = qty_required
                    reserved += 1
                    status = "ok"
                    message = "Reserved from stock"
                except HTTPException as exc:
                    status = "shortage"
                    shortage += 1
                    message = str(exc.detail)
            else:
                status = "shortage"
                shortage += 1
                message = f"Only {available} available of {qty_required} required"

            expected_delivery: datetime | None = None
            if status != "ok" and auto_purchase_request:
                if purchase_request is None:
                    purchase_request = self._ensure_planning_purchase_request(
                        organization_id, work_package_id, username, now
                    )
                self.repo.add_purchase_request_line(
                    PurchaseRequestLine(
                        organization_id=organization_id,
                        purchase_request_id=purchase_request.id,
                        part_master_id=part.id,
                        qty=qty_required - available if qty_required > available else qty_required,
                        needed_by=None,
                        status="open",
                    )
                )
                status = "purchase_required"
                shortage -= 1
                purchase_required += 1
                message = f"{message}; added to purchase request {purchase_request.request_number}"

            results.append(
                MaterialPlanningLineResult(
                    parts_plan_line_id=line_id,
                    part_number=part.oem_part_number,
                    part_master_id=part.id,
                    qty_required=qty_required,
                    qty_available=available,
                    qty_reserved=qty_reserved,
                    status=status,
                    reservation_id=reservation_id,
                    purchase_request_id=purchase_request.id if status == "purchase_required" and purchase_request else None,
                    expected_delivery=expected_delivery,
                    message=message,
                )
            )

        self._audit_required(
            actor,
            action="logistics.planning.material",
            target_type="work_package",
            target_id=work_package_id or organization_id,
            organization_id=organization_id,
            details=f"lines={len(results)};reserved={reserved};shortage={shortage};purchase={purchase_required}",
        )
        self._commit_or_conflict(detail="Material planning conflict")
        return MaterialPlanningResult(
            organization_id=organization_id,
            work_package_id=work_package_id,
            generated_at=now,
            reserved_lines=reserved,
            shortage_lines=shortage,
            purchase_required_lines=purchase_required,
            purchase_request_id=purchase_request.id if purchase_request else None,
            lines=results,
        )

    def _ensure_planning_purchase_request(
        self, org_id: str, work_package_id: str | None, username: str, now: datetime
    ) -> PurchaseRequest:
        if work_package_id:
            existing = self.repo.find_open_auto_purchase_request(org_id, work_package_id)
            if existing is not None:
                return existing
        row = PurchaseRequest(
            organization_id=org_id,
            request_number=_number("PR"),
            status="draft",
            requested_by=username,
            work_package_id=work_package_id,
            notes="Auto-raised by material planning",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_purchase_request(row)
        self.repo.flush()
        return row

    def run_tool_planning(
        self,
        organization_id: str,
        work_package_id: str | None,
        tool_plan_lines: list[dict[str, object]],
        *,
        username: str = "system",
        actor: ActorContext | None = None,
    ) -> ToolPlanningResult:
        """Reserve calibrated tools for planned tool lines and flag gaps."""
        now = _utcnow()
        results: list[ToolPlanningLineResult] = []
        reserved = unavailable = 0
        planning_actor = actor or ActorContext(username=username, role="", organization_id=organization_id)

        for raw in tool_plan_lines:
            line_id = str(raw.get("id") or "")
            tool_code = str(raw.get("tool_code") or "").strip()
            if not tool_code:
                unavailable += 1
                results.append(
                    ToolPlanningLineResult(
                        tool_plan_line_id=line_id,
                        tool_code="",
                        status="unavailable",
                        message="Plan line has no tool code",
                    )
                )
                continue
            tool = self.repo.get_tool_by_code(organization_id, tool_code.upper())
            if tool is None:
                unavailable += 1
                results.append(
                    ToolPlanningLineResult(
                        tool_plan_line_id=line_id,
                        tool_code=tool_code,
                        status="unavailable",
                        message="Tool is not registered in the tool store",
                    )
                )
                continue
            calibration_status = self._calibration_status(
                _truthy(tool.calibration_required), tool.calibration_due_at, now
            )
            if calibration_status == "overdue":
                tool.calibration_status = "overdue"
                tool.status = "calibration_due"
                tool.updated_at = now
                unavailable += 1
                results.append(
                    ToolPlanningLineResult(
                        tool_plan_line_id=line_id,
                        tool_code=tool.tool_code,
                        tool_id=tool.id,
                        status="overdue_cal",
                        calibration_status=calibration_status,
                        calibration_expires_at=tool.calibration_due_at,
                        message="Calibration overdue; tool cannot be planned",
                    )
                )
                continue
            if tool.status != "available":
                unavailable += 1
                results.append(
                    ToolPlanningLineResult(
                        tool_plan_line_id=line_id,
                        tool_code=tool.tool_code,
                        tool_id=tool.id,
                        status="unavailable",
                        calibration_status=calibration_status,
                        calibration_expires_at=tool.calibration_due_at,
                        message=f"Tool is '{tool.status}'",
                    )
                )
                continue
            reservation = self._reserve_tool_row(
                organization_id, tool, work_package_id, line_id or None, planning_actor
            )
            tool.calibration_status = calibration_status
            reserved += 1
            results.append(
                ToolPlanningLineResult(
                    tool_plan_line_id=line_id,
                    tool_code=tool.tool_code,
                    tool_id=tool.id,
                    status="reserved",
                    calibration_status=calibration_status,
                    calibration_expires_at=tool.calibration_due_at,
                    reservation_id=reservation.id,
                    message="Reserved for work package",
                )
            )

        self._audit_required(
            actor,
            action="logistics.planning.tools",
            target_type="work_package",
            target_id=work_package_id or organization_id,
            organization_id=organization_id,
            details=f"lines={len(results)};reserved={reserved};unavailable={unavailable}",
        )
        self._commit_or_conflict(detail="Tool planning conflict")
        return ToolPlanningResult(
            organization_id=organization_id,
            work_package_id=work_package_id,
            generated_at=now,
            reserved_lines=reserved,
            unavailable_lines=unavailable,
            lines=results,
        )

    # ------------------------------------------------------------------
    # Demo seed
    # ------------------------------------------------------------------
    def seed_demo(self, organization_id: str = "org-aviation-east", *, actor: ActorContext | None = None) -> SeedDemoOut:
        """Idempotent Program B demo dataset: warehouse tree, parts, stock, tools, vendor."""
        if self.org.repo.get_organization(organization_id) is None:
            return SeedDemoOut(
                organization_id=organization_id,
                created=False,
                warehouse_id="",
                message="Organization not found; nothing seeded",
            )
        existing = self.repo.get_warehouse_by_code(organization_id, "WH-MAIN")
        if existing is not None:
            return SeedDemoOut(
                organization_id=organization_id,
                created=False,
                warehouse_id=existing.id,
                message="Logistics demo data already present",
            )

        now = _utcnow()
        warehouse, locations = self._build_warehouse_tree(
            organization_id,
            code="WH-MAIN",
            name="Main Stores — YUL",
            warehouse_type="physical",
            is_bonded=False,
            address="Hangar 1, Montreal-Trudeau International",
            building_code="BLD-1",
            store_code="ST-1",
            room_code="RM-1",
            zone_types=["receiving", "quarantine", "hazmat", "shipping", "general"],
            bins_per_zone=2,
        )
        by_type: dict[str, Location] = {}
        for location in locations:
            by_type.setdefault(location.location_type, location)
        general = by_type["general"]
        hazmat = by_type["hazmat"]

        consumable = PartMaster(
            organization_id=organization_id,
            manufacturer="Airbus",
            oem_part_number="MS21042L3",
            customer_part_number="AE-MS21042L3",
            description="Self-locking nut, reduced hex",
            ata_chapter_id="ata-20-00",
            nsn="5310-00-123-4567",
            part_class="consumable",
            is_serialized="false",
            is_life_limited="false",
            issue_policy="FIFO",
            min_stock=Decimal("50"),
            max_stock=Decimal("500"),
            reorder_point=Decimal("100"),
            unit_of_measure="EA",
            status="active",
            created_at=now,
            updated_at=now,
        )
        sealant = PartMaster(
            organization_id=organization_id,
            manufacturer="PPG",
            oem_part_number="PR-1440-B2",
            description="Fuel tank sealant, class B — shelf life controlled",
            ata_chapter_id="ata-28-00",
            part_class="consumable",
            is_serialized="false",
            shelf_life_days=180,
            is_hazmat="true",
            is_dangerous_goods="true",
            issue_policy="FEFO",
            min_stock=Decimal("2"),
            max_stock=Decimal("20"),
            reorder_point=Decimal("4"),
            unit_of_measure="KIT",
            status="active",
            created_at=now,
            updated_at=now,
        )
        rotable = PartMaster(
            organization_id=organization_id,
            manufacturer="Collins Aerospace",
            oem_part_number="3214-1000-1",
            description="Main landing gear wheel assembly",
            ata_chapter_id="ata-32-00",
            part_class="rotable",
            is_serialized="true",
            is_life_limited="true",
            issue_policy="FIFO",
            min_stock=Decimal("1"),
            max_stock=Decimal("6"),
            reorder_point=Decimal("2"),
            unit_of_measure="EA",
            status="active",
            created_at=now,
            updated_at=now,
        )
        for part in (consumable, sealant, rotable):
            self.repo.add_part(part)
        self.repo.flush()

        self._receive_into_stock(
            organization_id,
            part=consumable,
            location=general,
            qty=Decimal("250"),
            condition="serviceable",
            performed_by="system",
            lot_number="LOT-2026-014",
            reference_type="seed",
            reference_id="seed",
            notes="Demo opening stock",
            now=now - timedelta(days=40),
        )
        self._receive_into_stock(
            organization_id,
            part=consumable,
            location=general,
            qty=Decimal("120"),
            condition="serviceable",
            performed_by="system",
            lot_number="LOT-2026-027",
            reference_type="seed",
            reference_id="seed",
            notes="Demo replenishment",
            now=now - timedelta(days=8),
        )
        self._receive_into_stock(
            organization_id,
            part=sealant,
            location=hazmat,
            qty=Decimal("6"),
            condition="serviceable",
            performed_by="system",
            batch_number="BATCH-A",
            lot_number="LOT-SEAL-A",
            expires_at=now + timedelta(days=20),
            reference_type="seed",
            reference_id="seed",
            notes="FEFO near-expiry batch",
            now=now - timedelta(days=160),
        )
        self._receive_into_stock(
            organization_id,
            part=sealant,
            location=hazmat,
            qty=Decimal("8"),
            condition="serviceable",
            performed_by="system",
            batch_number="BATCH-B",
            lot_number="LOT-SEAL-B",
            expires_at=now + timedelta(days=150),
            reference_type="seed",
            reference_id="seed",
            notes="FEFO fresh batch",
            now=now - timedelta(days=30),
        )
        rotable_unit = self._receive_into_stock(
            organization_id,
            part=rotable,
            location=general,
            qty=Decimal("2"),
            condition="serviceable",
            performed_by="system",
            serial_number="SN-MLG-00417",
            warranty_expires_at=now + timedelta(days=365),
            reference_type="seed",
            reference_id="seed",
            notes="Serialized rotable pool",
            now=now - timedelta(days=90),
        )
        rotable_unit.tsn_hours = Decimal("4200.00")
        rotable_unit.csn_cycles = 3100

        torque_wrench = Tool(
            organization_id=organization_id,
            tool_code="TL-TQ-001",
            description="Torque wrench 20-100 Nm",
            serial_number="TQ-2231",
            location_id=general.id,
            status="available",
            calibration_required="true",
            calibration_due_at=now + timedelta(days=120),
            calibration_status="current",
            created_at=now,
            updated_at=now,
        )
        borescope = Tool(
            organization_id=organization_id,
            tool_code="TL-BS-002",
            description="Video borescope, engine inspection",
            serial_number="BS-8890",
            location_id=general.id,
            status="available",
            calibration_required="true",
            calibration_due_at=now + timedelta(days=15),
            calibration_status="due_soon",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_tool(torque_wrench)
        self.repo.add_tool(borescope)
        self.repo.flush()
        self.repo.add_tool_calibration(
            ToolCalibration(
                organization_id=organization_id,
                tool_id=torque_wrench.id,
                calibrated_at=now - timedelta(days=245),
                due_at=now + timedelta(days=120),
                certificate_number="CAL-2025-8841",
                performed_by="system",
                notes="Seeded calibration record",
                created_at=now,
            )
        )
        for tool in (torque_wrench, borescope):
            self.repo.add_tool_history(
                ToolHistory(
                    organization_id=organization_id,
                    tool_id=tool.id,
                    event_type="created",
                    details="Seeded demo tool",
                    performed_by="system",
                    created_at=now,
                )
            )

        vendor = Vendor(
            organization_id=organization_id,
            code="VEN-AEROSUP",
            name="AeroSupply International",
            vendor_type="distributor",
            certificates="EASA Part-145; AS9120",
            approvals="Transport Canada AMO 12-34",
            contacts="orders@aerosupply.example",
            rating=Decimal("4.50"),
            lead_time_days=10,
            performance_score=Decimal("92.00"),
            warranty_terms="12 months from delivery",
            repair_capability="false",
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_vendor(vendor)
        self.repo.flush()

        for part, code in (
            (consumable, "MS21042L3"),
            (sealant, "PR1440B2"),
            (rotable, "32141000-1"),
        ):
            self.repo.add_identifier(
                PartIdentifier(
                    organization_id=organization_id,
                    part_master_id=part.id,
                    identifier_type="barcode",
                    value=code,
                    status="active",
                    created_at=now,
                )
            )
        self.repo.add_identifier(
            PartIdentifier(
                organization_id=organization_id,
                stock_unit_id=rotable_unit.id,
                identifier_type="qr",
                value="SN-MLG-00417",
                status="active",
                created_at=now,
            )
        )
        self.repo.add_identifier(
            PartIdentifier(
                organization_id=organization_id,
                tool_id=torque_wrench.id,
                identifier_type="rfid",
                value="RFID-TLTQ001",
                status="active",
                created_at=now,
            )
        )

        material_request = MaterialRequest(
            organization_id=organization_id,
            request_number=_number("MR"),
            requested_by="system",
            status="requested",
            notes="Seeded demo material request",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_material_request(material_request)
        self.repo.flush()
        self.repo.add_material_request_line(
            MaterialRequestLine(
                organization_id=organization_id,
                material_request_id=material_request.id,
                part_master_id=consumable.id,
                qty_requested=Decimal("20"),
                status="requested",
            )
        )
        self.repo.add_material_request_line(
            MaterialRequestLine(
                organization_id=organization_id,
                material_request_id=material_request.id,
                part_master_id=sealant.id,
                qty_requested=Decimal("2"),
                status="requested",
            )
        )

        self._commit_or_conflict(detail="Logistics seed conflict")
        return SeedDemoOut(
            organization_id=organization_id,
            created=True,
            warehouse_id=warehouse.id,
            location_ids=[loc.id for loc in locations],
            part_ids=[consumable.id, sealant.id, rotable.id],
            tool_ids=[torque_wrench.id, borescope.id],
            vendor_ids=[vendor.id],
            material_request_id=material_request.id,
            message="Logistics demo data created",
        )

    def ensure_seed_data(self) -> None:
        """Boot-time hook mirroring the other Mercury domain services."""
        try:
            self.seed_demo("org-aviation-east")
        except HTTPException:
            self.repo.rollback()
            logger.exception("logistics seed skipped")
