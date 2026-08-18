"""Program B – Enterprise Logistics data access.

Every query is organization-scoped; callers must pass the resolved organization id.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

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

MAX_PAGE = 500


def _page(limit: int, offset: int) -> tuple[int, int]:
    return min(max(int(limit), 1), MAX_PAGE), max(int(offset), 0)


class LogisticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- unit of work ---
    def add(self, row: object) -> object:
        self.db.add(row)
        return row

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)

    # ------------------------------------------------------------------
    # Warehouse hierarchy
    # ------------------------------------------------------------------
    def add_warehouse(self, row: Warehouse) -> Warehouse:
        self.db.add(row)
        return row

    def get_warehouse(self, organization_id: str, warehouse_id: str) -> Warehouse | None:
        return self.db.scalars(
            select(Warehouse).where(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == organization_id,
                Warehouse.deleted_at.is_(None),
            )
        ).first()

    def get_warehouse_by_code(self, organization_id: str, code: str) -> Warehouse | None:
        return self.db.scalars(
            select(Warehouse).where(
                Warehouse.organization_id == organization_id,
                Warehouse.code == code,
                Warehouse.deleted_at.is_(None),
            )
        ).first()

    def list_warehouses(self, *, organization_id: str, limit: int = 100, offset: int = 0) -> list[Warehouse]:
        lim, off = _page(limit, offset)
        return list(
            self.db.scalars(
                select(Warehouse)
                .where(Warehouse.organization_id == organization_id, Warehouse.deleted_at.is_(None))
                .order_by(Warehouse.code)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def count_warehouses(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(Warehouse)
                .where(Warehouse.organization_id == organization_id, Warehouse.deleted_at.is_(None))
            )
            or 0
        )

    def add_building(self, row: Building) -> Building:
        self.db.add(row)
        return row

    def add_store_area(self, row: StoreArea) -> StoreArea:
        self.db.add(row)
        return row

    def add_room(self, row: Room) -> Room:
        self.db.add(row)
        return row

    def add_zone(self, row: Zone) -> Zone:
        self.db.add(row)
        return row

    def add_aisle(self, row: Aisle) -> Aisle:
        self.db.add(row)
        return row

    def add_shelf(self, row: Shelf) -> Shelf:
        self.db.add(row)
        return row

    def add_bin(self, row: Bin) -> Bin:
        self.db.add(row)
        return row

    def add_location(self, row: Location) -> Location:
        self.db.add(row)
        return row

    def get_location(self, organization_id: str, location_id: str) -> Location | None:
        return self.db.scalars(
            select(Location).where(Location.id == location_id, Location.organization_id == organization_id)
        ).first()

    def get_location_by_code(self, organization_id: str, location_code: str) -> Location | None:
        return self.db.scalars(
            select(Location).where(
                Location.organization_id == organization_id, Location.location_code == location_code
            )
        ).first()

    def list_locations(
        self,
        *,
        organization_id: str,
        warehouse_id: str | None = None,
        location_type: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Location]:
        lim, off = _page(limit, offset)
        stmt: Select[tuple[Location]] = select(Location).where(Location.organization_id == organization_id)
        if warehouse_id:
            stmt = stmt.where(Location.warehouse_id == warehouse_id)
        if location_type:
            stmt = stmt.where(Location.location_type == location_type)
        return list(self.db.scalars(stmt.order_by(Location.location_code).limit(lim).offset(off)).all())

    def first_location_of_type(self, organization_id: str, location_type: str) -> Location | None:
        return self.db.scalars(
            select(Location)
            .where(
                Location.organization_id == organization_id,
                Location.location_type == location_type,
                Location.status == "active",
            )
            .order_by(Location.location_code)
        ).first()

    def count_locations(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(Location).where(Location.organization_id == organization_id)
            )
            or 0
        )

    # ------------------------------------------------------------------
    # Part master
    # ------------------------------------------------------------------
    def add_part(self, row: PartMaster) -> PartMaster:
        self.db.add(row)
        return row

    def get_part(self, organization_id: str, part_id: str, *, for_update: bool = False) -> PartMaster | None:
        stmt = select(PartMaster).where(
            PartMaster.id == part_id,
            PartMaster.organization_id == organization_id,
            PartMaster.deleted_at.is_(None),
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def get_part_by_number(self, organization_id: str, part_number: str) -> PartMaster | None:
        return self.db.scalars(
            select(PartMaster)
            .where(
                PartMaster.organization_id == organization_id,
                PartMaster.deleted_at.is_(None),
                or_(
                    PartMaster.oem_part_number == part_number,
                    PartMaster.customer_part_number == part_number,
                ),
            )
            .order_by(PartMaster.oem_part_number)
        ).first()

    def list_parts(
        self,
        *,
        organization_id: str,
        q: str | None = None,
        part_class: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartMaster]:
        lim, off = _page(limit, offset)
        stmt: Select[tuple[PartMaster]] = select(PartMaster).where(
            PartMaster.organization_id == organization_id,
            PartMaster.deleted_at.is_(None),
        )
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    PartMaster.oem_part_number.ilike(like),
                    PartMaster.customer_part_number.ilike(like),
                    PartMaster.description.ilike(like),
                    PartMaster.nsn.ilike(like),
                )
            )
        if part_class:
            stmt = stmt.where(PartMaster.part_class == part_class)
        if status:
            stmt = stmt.where(PartMaster.status == status)
        return list(self.db.scalars(stmt.order_by(PartMaster.oem_part_number).limit(lim).offset(off)).all())

    def count_parts(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PartMaster)
                .where(PartMaster.organization_id == organization_id, PartMaster.deleted_at.is_(None))
            )
            or 0
        )

    def add_identifier(self, row: PartIdentifier) -> PartIdentifier:
        self.db.add(row)
        return row

    def get_identifier(
        self, organization_id: str, value: str, *, identifier_type: str | None = None
    ) -> PartIdentifier | None:
        stmt = select(PartIdentifier).where(
            PartIdentifier.organization_id == organization_id,
            PartIdentifier.value == value,
            PartIdentifier.status == "active",
        )
        if identifier_type:
            stmt = stmt.where(PartIdentifier.identifier_type == identifier_type)
        return self.db.scalars(stmt).first()

    def list_identifiers(self, *, organization_id: str, part_master_id: str) -> list[PartIdentifier]:
        return list(
            self.db.scalars(
                select(PartIdentifier).where(
                    PartIdentifier.organization_id == organization_id,
                    PartIdentifier.part_master_id == part_master_id,
                )
            ).all()
        )

    def add_attachment(self, row: PartAttachment) -> PartAttachment:
        self.db.add(row)
        return row

    def list_attachments(self, *, organization_id: str, part_master_id: str) -> list[PartAttachment]:
        return list(
            self.db.scalars(
                select(PartAttachment)
                .where(
                    PartAttachment.organization_id == organization_id,
                    PartAttachment.part_master_id == part_master_id,
                )
                .order_by(PartAttachment.created_at.desc())
            ).all()
        )

    def add_family(self, row: PartFamily) -> PartFamily:
        self.db.add(row)
        return row

    def get_family(self, organization_id: str, family_id: str) -> PartFamily | None:
        return self.db.scalars(
            select(PartFamily).where(PartFamily.id == family_id, PartFamily.organization_id == organization_id)
        ).first()

    def get_family_by_code(self, organization_id: str, code: str) -> PartFamily | None:
        return self.db.scalars(
            select(PartFamily).where(PartFamily.organization_id == organization_id, PartFamily.code == code)
        ).first()

    def list_families(self, *, organization_id: str, limit: int = 100, offset: int = 0) -> list[PartFamily]:
        lim, off = _page(limit, offset)
        return list(
            self.db.scalars(
                select(PartFamily)
                .where(PartFamily.organization_id == organization_id)
                .order_by(PartFamily.code)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def add_family_member(self, row: PartFamilyMember) -> PartFamilyMember:
        self.db.add(row)
        return row

    def list_family_members(self, *, organization_id: str, family_id: str) -> list[PartFamilyMember]:
        return list(
            self.db.scalars(
                select(PartFamilyMember).where(
                    PartFamilyMember.organization_id == organization_id,
                    PartFamilyMember.family_id == family_id,
                )
            ).all()
        )

    def add_supersession(self, row: PartSupersession) -> PartSupersession:
        self.db.add(row)
        return row

    def list_supersessions(self, *, organization_id: str, part_master_id: str | None = None) -> list[PartSupersession]:
        stmt = select(PartSupersession).where(PartSupersession.organization_id == organization_id)
        if part_master_id:
            stmt = stmt.where(
                or_(
                    PartSupersession.from_part_id == part_master_id,
                    PartSupersession.to_part_id == part_master_id,
                )
            )
        return list(self.db.scalars(stmt.order_by(PartSupersession.created_at.desc())).all())

    # ------------------------------------------------------------------
    # Stock balances / units / movements
    # ------------------------------------------------------------------
    def get_balance(
        self, organization_id: str, part_master_id: str, location_id: str, condition: str
    ) -> StockBalance | None:
        return self.db.scalars(
            select(StockBalance).where(
                StockBalance.organization_id == organization_id,
                StockBalance.part_master_id == part_master_id,
                StockBalance.location_id == location_id,
                StockBalance.condition == condition,
            )
        ).first()

    def get_or_create_balance(
        self, organization_id: str, part_master_id: str, location_id: str, condition: str, *, now: datetime
    ) -> StockBalance:
        row = self.get_balance(organization_id, part_master_id, location_id, condition)
        if row is not None:
            return row
        row = StockBalance(
            organization_id=organization_id,
            part_master_id=part_master_id,
            location_id=location_id,
            condition=condition,
            qty_on_hand=Decimal("0"),
            qty_reserved=Decimal("0"),
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_balances(
        self,
        *,
        organization_id: str,
        part_master_id: str | None = None,
        location_id: str | None = None,
        condition: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[StockBalance]:
        lim, off = _page(limit, offset)
        stmt: Select[tuple[StockBalance]] = select(StockBalance).where(
            StockBalance.organization_id == organization_id
        )
        if part_master_id:
            stmt = stmt.where(StockBalance.part_master_id == part_master_id)
        if location_id:
            stmt = stmt.where(StockBalance.location_id == location_id)
        if condition:
            stmt = stmt.where(StockBalance.condition == condition)
        return list(self.db.scalars(stmt.order_by(StockBalance.part_master_id).limit(lim).offset(off)).all())

    def list_balances_detailed(
        self,
        *,
        organization_id: str,
        part_master_id: str | None = None,
        location_id: str | None = None,
        condition: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[tuple[StockBalance, PartMaster, Location]]:
        """Single joined query so balance listings never fan out into N+1 lookups."""
        lim, off = _page(limit, offset)
        stmt = (
            select(StockBalance, PartMaster, Location)
            .join(PartMaster, PartMaster.id == StockBalance.part_master_id)
            .join(Location, Location.id == StockBalance.location_id)
            .where(StockBalance.organization_id == organization_id)
        )
        if part_master_id:
            stmt = stmt.where(StockBalance.part_master_id == part_master_id)
        if location_id:
            stmt = stmt.where(StockBalance.location_id == location_id)
        if condition:
            stmt = stmt.where(StockBalance.condition == condition)
        rows = self.db.execute(
            stmt.order_by(PartMaster.oem_part_number, Location.location_code).limit(lim).offset(off)
        ).all()
        return [(r[0], r[1], r[2]) for r in rows]

    def available_qty(
        self,
        organization_id: str,
        part_master_id: str,
        *,
        location_id: str | None = None,
        condition: str = "serviceable",
    ) -> Decimal:
        stmt = select(
            func.coalesce(func.sum(StockBalance.qty_on_hand - StockBalance.qty_reserved), 0)
        ).where(
            StockBalance.organization_id == organization_id,
            StockBalance.part_master_id == part_master_id,
            StockBalance.condition == condition,
        )
        if location_id:
            stmt = stmt.where(StockBalance.location_id == location_id)
        return Decimal(str(self.db.scalar(stmt) or 0))

    def balances_with_availability(
        self, organization_id: str, part_master_id: str, *, condition: str = "serviceable"
    ) -> list[StockBalance]:
        return list(
            self.db.scalars(
                select(StockBalance)
                .where(
                    StockBalance.organization_id == organization_id,
                    StockBalance.part_master_id == part_master_id,
                    StockBalance.condition == condition,
                    StockBalance.qty_on_hand > StockBalance.qty_reserved,
                )
                .order_by(StockBalance.updated_at)
            ).all()
        )

    def balances_in_warehouse(
        self, organization_id: str, part_master_id: str, warehouse_id: str, *, condition: str = "serviceable"
    ) -> list[StockBalance]:
        return list(
            self.db.scalars(
                select(StockBalance)
                .join(Location, Location.id == StockBalance.location_id)
                .where(
                    StockBalance.organization_id == organization_id,
                    StockBalance.part_master_id == part_master_id,
                    StockBalance.condition == condition,
                    StockBalance.qty_on_hand > StockBalance.qty_reserved,
                    Location.warehouse_id == warehouse_id,
                )
                .order_by(StockBalance.updated_at)
            ).all()
        )

    def count_stock_lines(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(StockBalance).where(StockBalance.organization_id == organization_id)
            )
            or 0
        )

    def sum_stock(self, organization_id: str) -> tuple[Decimal, Decimal]:
        row = self.db.execute(
            select(
                func.coalesce(func.sum(StockBalance.qty_on_hand), 0),
                func.coalesce(func.sum(StockBalance.qty_reserved), 0),
            ).where(StockBalance.organization_id == organization_id)
        ).one()
        return Decimal(str(row[0] or 0)), Decimal(str(row[1] or 0))

    def count_low_stock_parts(self, organization_id: str) -> int:
        on_hand = (
            select(
                StockBalance.part_master_id.label("part_id"),
                func.coalesce(func.sum(StockBalance.qty_on_hand), 0).label("qty"),
            )
            .where(StockBalance.organization_id == organization_id)
            .group_by(StockBalance.part_master_id)
            .subquery()
        )
        stmt = (
            select(func.count())
            .select_from(PartMaster)
            .outerjoin(on_hand, on_hand.c.part_id == PartMaster.id)
            .where(
                PartMaster.organization_id == organization_id,
                PartMaster.deleted_at.is_(None),
                PartMaster.reorder_point > 0,
                func.coalesce(on_hand.c.qty, 0) <= PartMaster.reorder_point,
            )
        )
        return int(self.db.scalar(stmt) or 0)

    def list_shortage_parts(self, organization_id: str, *, limit: int = 100) -> list[tuple[PartMaster, Decimal]]:
        """Parts at or below reorder (including zero on-hand)."""
        on_hand = (
            select(
                StockBalance.part_master_id.label("part_id"),
                func.coalesce(func.sum(StockBalance.qty_on_hand - StockBalance.qty_reserved), 0).label("qty"),
            )
            .where(StockBalance.organization_id == organization_id)
            .group_by(StockBalance.part_master_id)
            .subquery()
        )
        stmt = (
            select(PartMaster, func.coalesce(on_hand.c.qty, 0))
            .outerjoin(on_hand, on_hand.c.part_id == PartMaster.id)
            .where(
                PartMaster.organization_id == organization_id,
                PartMaster.deleted_at.is_(None),
                PartMaster.status == "active",
                or_(
                    and_(PartMaster.reorder_point > 0, func.coalesce(on_hand.c.qty, 0) <= PartMaster.reorder_point),
                    func.coalesce(on_hand.c.qty, 0) <= 0,
                ),
            )
            .order_by(PartMaster.oem_part_number)
            .limit(max(1, min(limit, 500)))
        )
        return [(row[0], Decimal(str(row[1] or 0))) for row in self.db.execute(stmt).all()]

    def count_quarantine_lines(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(StockBalance)
                .where(
                    StockBalance.organization_id == organization_id,
                    StockBalance.condition == "quarantine",
                    StockBalance.qty_on_hand > 0,
                )
            )
            or 0
        )

    def add_stock_unit(self, row: StockUnit) -> StockUnit:
        self.db.add(row)
        return row

    def get_stock_unit(self, organization_id: str, unit_id: str, *, for_update: bool = False) -> StockUnit | None:
        stmt = select(StockUnit).where(StockUnit.id == unit_id, StockUnit.organization_id == organization_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_stock_units(
        self,
        *,
        organization_id: str,
        part_master_id: str | None = None,
        location_id: str | None = None,
        condition: str | None = None,
        serial_number: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[StockUnit]:
        lim, off = _page(limit, offset)
        stmt: Select[tuple[StockUnit]] = select(StockUnit).where(StockUnit.organization_id == organization_id)
        if part_master_id:
            stmt = stmt.where(StockUnit.part_master_id == part_master_id)
        if location_id:
            stmt = stmt.where(StockUnit.location_id == location_id)
        if condition:
            stmt = stmt.where(StockUnit.condition == condition)
        if serial_number:
            stmt = stmt.where(StockUnit.serial_number == serial_number)
        return list(self.db.scalars(stmt.order_by(StockUnit.created_at.desc()).limit(lim).offset(off)).all())

    def pickable_units(
        self,
        *,
        organization_id: str,
        part_master_id: str,
        location_id: str | None,
        condition: str,
        policy: str,
    ) -> list[StockUnit]:
        """Consumable/lot units ordered by the part's issue policy (FEFO or FIFO)."""
        stmt = select(StockUnit).where(
            StockUnit.organization_id == organization_id,
            StockUnit.part_master_id == part_master_id,
            StockUnit.condition == condition,
            StockUnit.status == "active",
            StockUnit.qty > 0,
        )
        if location_id:
            stmt = stmt.where(StockUnit.location_id == location_id)
        if policy.upper() == "FEFO":
            stmt = stmt.order_by(
                StockUnit.expires_at.asc().nullslast(),
                StockUnit.received_at.asc().nullsfirst(),
                StockUnit.created_at.asc(),
            )
        else:
            stmt = stmt.order_by(
                StockUnit.received_at.asc().nullsfirst(),
                StockUnit.created_at.asc(),
            )
        return list(self.db.scalars(stmt).all())

    def count_expiring_units(self, organization_id: str, *, before: datetime, after: datetime | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(StockUnit)
            .where(
                StockUnit.organization_id == organization_id,
                StockUnit.status == "active",
                StockUnit.qty > 0,
                StockUnit.expires_at.is_not(None),
                StockUnit.expires_at <= before,
            )
        )
        if after is not None:
            stmt = stmt.where(StockUnit.expires_at > after)
        return int(self.db.scalar(stmt) or 0)

    def add_movement(self, row: StockMovement) -> StockMovement:
        self.db.add(row)
        return row

    def list_movements(
        self,
        *,
        organization_id: str,
        part_master_id: str | None = None,
        movement_type: str | None = None,
        reference_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StockMovement]:
        lim, off = _page(limit, offset)
        stmt: Select[tuple[StockMovement]] = select(StockMovement).where(
            StockMovement.organization_id == organization_id
        )
        if part_master_id:
            stmt = stmt.where(StockMovement.part_master_id == part_master_id)
        if movement_type:
            stmt = stmt.where(StockMovement.movement_type == movement_type)
        if reference_id:
            stmt = stmt.where(StockMovement.reference_id == reference_id)
        if since is not None:
            stmt = stmt.where(StockMovement.created_at >= since)
        return list(self.db.scalars(stmt.order_by(StockMovement.created_at.desc()).limit(lim).offset(off)).all())

    def count_movements(self, organization_id: str, *, since: datetime) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(StockMovement)
                .where(StockMovement.organization_id == organization_id, StockMovement.created_at >= since)
            )
            or 0
        )

    # ------------------------------------------------------------------
    # Reservations
    # ------------------------------------------------------------------
    def add_reservation(self, row: StockReservation) -> StockReservation:
        self.db.add(row)
        return row

    def get_reservation(
        self, organization_id: str, reservation_id: str, *, for_update: bool = False
    ) -> StockReservation | None:
        stmt = select(StockReservation).where(
            StockReservation.id == reservation_id,
            StockReservation.organization_id == organization_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_reservations(
        self,
        *,
        organization_id: str,
        status: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        part_master_id: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[StockReservation]:
        lim, off = _page(limit, offset)
        stmt: Select[tuple[StockReservation]] = select(StockReservation).where(
            StockReservation.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(StockReservation.status == status)
        if source_type:
            stmt = stmt.where(StockReservation.source_type == source_type)
        if source_id:
            stmt = stmt.where(StockReservation.source_id == source_id)
        if part_master_id:
            stmt = stmt.where(StockReservation.part_master_id == part_master_id)
        return list(self.db.scalars(stmt.order_by(StockReservation.created_at.desc()).limit(lim).offset(off)).all())

    def count_reservations(self, organization_id: str, *, status: str = "open") -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(StockReservation)
                .where(StockReservation.organization_id == organization_id, StockReservation.status == status)
            )
            or 0
        )

    # ------------------------------------------------------------------
    # Transfers
    # ------------------------------------------------------------------
    def add_transfer(self, row: WarehouseTransfer) -> WarehouseTransfer:
        self.db.add(row)
        return row

    def get_transfer(
        self, organization_id: str, transfer_id: str, *, for_update: bool = False
    ) -> WarehouseTransfer | None:
        stmt = select(WarehouseTransfer).where(
            WarehouseTransfer.id == transfer_id,
            WarehouseTransfer.organization_id == organization_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_transfers(
        self, *, organization_id: str, status: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[WarehouseTransfer]:
        lim, off = _page(limit, offset)
        stmt = select(WarehouseTransfer).where(WarehouseTransfer.organization_id == organization_id)
        if status:
            stmt = stmt.where(WarehouseTransfer.status == status)
        return list(self.db.scalars(stmt.order_by(WarehouseTransfer.created_at.desc()).limit(lim).offset(off)).all())

    def add_transfer_line(self, row: WarehouseTransferLine) -> WarehouseTransferLine:
        self.db.add(row)
        return row

    def list_transfer_lines(self, *, organization_id: str, transfer_id: str) -> list[WarehouseTransferLine]:
        return list(
            self.db.scalars(
                select(WarehouseTransferLine).where(
                    WarehouseTransferLine.organization_id == organization_id,
                    WarehouseTransferLine.transfer_id == transfer_id,
                )
            ).all()
        )

    # ------------------------------------------------------------------
    # Rotable cycles
    # ------------------------------------------------------------------
    def add_rotable_cycle(self, row: RotableCycle) -> RotableCycle:
        self.db.add(row)
        return row

    def get_rotable_cycle(
        self, organization_id: str, cycle_id: str, *, for_update: bool = False
    ) -> RotableCycle | None:
        stmt = select(RotableCycle).where(
            RotableCycle.id == cycle_id, RotableCycle.organization_id == organization_id
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_rotable_cycles(
        self,
        *,
        organization_id: str,
        status: str | None = None,
        stock_unit_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RotableCycle]:
        lim, off = _page(limit, offset)
        stmt = select(RotableCycle).where(RotableCycle.organization_id == organization_id)
        if status:
            stmt = stmt.where(RotableCycle.status == status)
        if stock_unit_id:
            stmt = stmt.where(RotableCycle.stock_unit_id == stock_unit_id)
        return list(self.db.scalars(stmt.order_by(RotableCycle.opened_at.desc()).limit(lim).offset(off)).all())

    def count_open_rotable_cycles(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(RotableCycle)
                .where(
                    RotableCycle.organization_id == organization_id,
                    RotableCycle.status.in_(("open", "in_repair")),
                )
            )
            or 0
        )

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    def add_tool(self, row: Tool) -> Tool:
        self.db.add(row)
        return row

    def get_tool(self, organization_id: str, tool_id: str, *, for_update: bool = False) -> Tool | None:
        stmt = select(Tool).where(
            Tool.id == tool_id, Tool.organization_id == organization_id, Tool.deleted_at.is_(None)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def get_tool_by_code(self, organization_id: str, tool_code: str) -> Tool | None:
        return self.db.scalars(
            select(Tool).where(
                Tool.organization_id == organization_id,
                Tool.tool_code == tool_code,
                Tool.deleted_at.is_(None),
            )
        ).first()

    def list_tools(
        self,
        *,
        organization_id: str,
        q: str | None = None,
        status: str | None = None,
        calibration_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Tool]:
        lim, off = _page(limit, offset)
        stmt: Select[tuple[Tool]] = select(Tool).where(
            Tool.organization_id == organization_id, Tool.deleted_at.is_(None)
        )
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(Tool.tool_code.ilike(like), Tool.description.ilike(like), Tool.serial_number.ilike(like))
            )
        if status:
            stmt = stmt.where(Tool.status == status)
        if calibration_status:
            stmt = stmt.where(Tool.calibration_status == calibration_status)
        return list(self.db.scalars(stmt.order_by(Tool.tool_code).limit(lim).offset(off)).all())

    def count_tools(self, organization_id: str, *, status: str | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(Tool)
            .where(Tool.organization_id == organization_id, Tool.deleted_at.is_(None))
        )
        if status:
            stmt = stmt.where(Tool.status == status)
        return int(self.db.scalar(stmt) or 0)

    def count_tools_calibration_due(self, organization_id: str, *, before: datetime) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(Tool)
                .where(
                    Tool.organization_id == organization_id,
                    Tool.deleted_at.is_(None),
                    Tool.calibration_required == "true",
                    Tool.calibration_due_at.is_not(None),
                    Tool.calibration_due_at <= before,
                )
            )
            or 0
        )

    def add_tool_calibration(self, row: ToolCalibration) -> ToolCalibration:
        self.db.add(row)
        return row

    def list_tool_calibrations(self, *, organization_id: str, tool_id: str) -> list[ToolCalibration]:
        return list(
            self.db.scalars(
                select(ToolCalibration)
                .where(ToolCalibration.organization_id == organization_id, ToolCalibration.tool_id == tool_id)
                .order_by(ToolCalibration.calibrated_at.desc())
            ).all()
        )

    def add_tool_issue(self, row: ToolIssue) -> ToolIssue:
        self.db.add(row)
        return row

    def get_open_tool_issue(self, organization_id: str, tool_id: str) -> ToolIssue | None:
        return self.db.scalars(
            select(ToolIssue)
            .where(
                ToolIssue.organization_id == organization_id,
                ToolIssue.tool_id == tool_id,
                ToolIssue.status == "issued",
            )
            .order_by(ToolIssue.issued_at.desc())
        ).first()

    def list_tool_issues(
        self, *, organization_id: str, tool_id: str | None = None, status: str | None = None, limit: int = 100
    ) -> list[ToolIssue]:
        lim, _ = _page(limit, 0)
        stmt = select(ToolIssue).where(ToolIssue.organization_id == organization_id)
        if tool_id:
            stmt = stmt.where(ToolIssue.tool_id == tool_id)
        if status:
            stmt = stmt.where(ToolIssue.status == status)
        return list(self.db.scalars(stmt.order_by(ToolIssue.issued_at.desc()).limit(lim)).all())

    def add_tool_reservation(self, row: ToolReservation) -> ToolReservation:
        self.db.add(row)
        return row

    def list_tool_reservations(
        self, *, organization_id: str, tool_id: str | None = None, status: str | None = None
    ) -> list[ToolReservation]:
        stmt = select(ToolReservation).where(ToolReservation.organization_id == organization_id)
        if tool_id:
            stmt = stmt.where(ToolReservation.tool_id == tool_id)
        if status:
            stmt = stmt.where(ToolReservation.status == status)
        return list(self.db.scalars(stmt.order_by(ToolReservation.created_at.desc())).all())

    def add_lost_tool_report(self, row: LostToolReport) -> LostToolReport:
        self.db.add(row)
        return row

    def list_lost_tool_reports(
        self, *, organization_id: str, status: str | None = None, limit: int = 100
    ) -> list[LostToolReport]:
        lim, _ = _page(limit, 0)
        stmt = select(LostToolReport).where(LostToolReport.organization_id == organization_id)
        if status:
            stmt = stmt.where(LostToolReport.status == status)
        return list(self.db.scalars(stmt.order_by(LostToolReport.created_at.desc()).limit(lim)).all())

    def count_lost_tool_reports(self, organization_id: str, *, status: str = "open") -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(LostToolReport)
                .where(LostToolReport.organization_id == organization_id, LostToolReport.status == status)
            )
            or 0
        )

    def add_tool_history(self, row: ToolHistory) -> ToolHistory:
        self.db.add(row)
        return row

    def list_tool_history(self, *, organization_id: str, tool_id: str, limit: int = 100) -> list[ToolHistory]:
        lim, _ = _page(limit, 0)
        return list(
            self.db.scalars(
                select(ToolHistory)
                .where(ToolHistory.organization_id == organization_id, ToolHistory.tool_id == tool_id)
                .order_by(ToolHistory.created_at.desc())
                .limit(lim)
            ).all()
        )

    # ------------------------------------------------------------------
    # Material requests
    # ------------------------------------------------------------------
    def add_material_request(self, row: MaterialRequest) -> MaterialRequest:
        self.db.add(row)
        return row

    def get_material_request(
        self, organization_id: str, request_id: str, *, for_update: bool = False
    ) -> MaterialRequest | None:
        stmt = select(MaterialRequest).where(
            MaterialRequest.id == request_id, MaterialRequest.organization_id == organization_id
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_material_requests(
        self,
        *,
        organization_id: str,
        status: str | None = None,
        work_package_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MaterialRequest]:
        lim, off = _page(limit, offset)
        stmt = select(MaterialRequest).where(MaterialRequest.organization_id == organization_id)
        if status:
            stmt = stmt.where(MaterialRequest.status == status)
        if work_package_id:
            stmt = stmt.where(MaterialRequest.work_package_id == work_package_id)
        return list(self.db.scalars(stmt.order_by(MaterialRequest.created_at.desc()).limit(lim).offset(off)).all())

    def count_material_requests(self, organization_id: str, *, statuses: tuple[str, ...]) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(MaterialRequest)
                .where(
                    MaterialRequest.organization_id == organization_id,
                    MaterialRequest.status.in_(statuses),
                )
            )
            or 0
        )

    def add_material_request_line(self, row: MaterialRequestLine) -> MaterialRequestLine:
        self.db.add(row)
        return row

    def get_material_request_line(self, organization_id: str, line_id: str) -> MaterialRequestLine | None:
        return self.db.scalars(
            select(MaterialRequestLine).where(
                MaterialRequestLine.id == line_id,
                MaterialRequestLine.organization_id == organization_id,
            )
        ).first()

    def list_material_request_lines(self, *, organization_id: str, request_id: str) -> list[MaterialRequestLine]:
        return list(
            self.db.scalars(
                select(MaterialRequestLine).where(
                    MaterialRequestLine.organization_id == organization_id,
                    MaterialRequestLine.material_request_id == request_id,
                )
            ).all()
        )

    # ------------------------------------------------------------------
    # Vendors
    # ------------------------------------------------------------------
    def add_vendor(self, row: Vendor) -> Vendor:
        self.db.add(row)
        return row

    def get_vendor(self, organization_id: str, vendor_id: str) -> Vendor | None:
        return self.db.scalars(
            select(Vendor).where(Vendor.id == vendor_id, Vendor.organization_id == organization_id)
        ).first()

    def get_vendor_by_code(self, organization_id: str, code: str) -> Vendor | None:
        return self.db.scalars(
            select(Vendor).where(Vendor.organization_id == organization_id, Vendor.code == code)
        ).first()

    def list_vendors(
        self,
        *,
        organization_id: str,
        q: str | None = None,
        vendor_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Vendor]:
        lim, off = _page(limit, offset)
        stmt: Select[tuple[Vendor]] = select(Vendor).where(Vendor.organization_id == organization_id)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(or_(Vendor.name.ilike(like), Vendor.code.ilike(like)))
        if vendor_type:
            stmt = stmt.where(Vendor.vendor_type == vendor_type)
        if status:
            stmt = stmt.where(Vendor.status == status)
        return list(self.db.scalars(stmt.order_by(Vendor.name).limit(lim).offset(off)).all())

    # ------------------------------------------------------------------
    # Purchasing
    # ------------------------------------------------------------------
    def add_purchase_request(self, row: PurchaseRequest) -> PurchaseRequest:
        self.db.add(row)
        return row

    def get_purchase_request(
        self, organization_id: str, request_id: str, *, for_update: bool = False
    ) -> PurchaseRequest | None:
        stmt = select(PurchaseRequest).where(
            PurchaseRequest.id == request_id, PurchaseRequest.organization_id == organization_id
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_purchase_requests(
        self, *, organization_id: str, status: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[PurchaseRequest]:
        lim, off = _page(limit, offset)
        stmt = select(PurchaseRequest).where(PurchaseRequest.organization_id == organization_id)
        if status:
            stmt = stmt.where(PurchaseRequest.status == status)
        return list(self.db.scalars(stmt.order_by(PurchaseRequest.created_at.desc()).limit(lim).offset(off)).all())

    def count_purchase_requests(self, organization_id: str, *, statuses: tuple[str, ...]) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PurchaseRequest)
                .where(
                    PurchaseRequest.organization_id == organization_id,
                    PurchaseRequest.status.in_(statuses),
                )
            )
            or 0
        )

    def find_open_auto_purchase_request(self, organization_id: str, work_package_id: str) -> PurchaseRequest | None:
        return self.db.scalars(
            select(PurchaseRequest)
            .where(
                PurchaseRequest.organization_id == organization_id,
                PurchaseRequest.work_package_id == work_package_id,
                PurchaseRequest.status == "draft",
            )
            .order_by(PurchaseRequest.created_at.desc())
        ).first()

    def add_purchase_request_line(self, row: PurchaseRequestLine) -> PurchaseRequestLine:
        self.db.add(row)
        return row

    def list_purchase_request_lines(self, *, organization_id: str, request_id: str) -> list[PurchaseRequestLine]:
        return list(
            self.db.scalars(
                select(PurchaseRequestLine).where(
                    PurchaseRequestLine.organization_id == organization_id,
                    PurchaseRequestLine.purchase_request_id == request_id,
                )
            ).all()
        )

    def add_rfq(self, row: Rfq) -> Rfq:
        self.db.add(row)
        return row

    def get_rfq(self, organization_id: str, rfq_id: str, *, for_update: bool = False) -> Rfq | None:
        stmt = select(Rfq).where(Rfq.id == rfq_id, Rfq.organization_id == organization_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_rfqs(
        self, *, organization_id: str, status: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[Rfq]:
        lim, off = _page(limit, offset)
        stmt = select(Rfq).where(Rfq.organization_id == organization_id)
        if status:
            stmt = stmt.where(Rfq.status == status)
        return list(self.db.scalars(stmt.order_by(Rfq.created_at.desc()).limit(lim).offset(off)).all())

    def add_quote(self, row: RfqQuote) -> RfqQuote:
        self.db.add(row)
        return row

    def get_quote(self, organization_id: str, quote_id: str) -> RfqQuote | None:
        return self.db.scalars(
            select(RfqQuote).where(RfqQuote.id == quote_id, RfqQuote.organization_id == organization_id)
        ).first()

    def list_quotes(self, *, organization_id: str, rfq_id: str) -> list[RfqQuote]:
        return list(
            self.db.scalars(
                select(RfqQuote)
                .where(RfqQuote.organization_id == organization_id, RfqQuote.rfq_id == rfq_id)
                .order_by(RfqQuote.unit_price)
            ).all()
        )

    def add_purchase_order(self, row: PurchaseOrder) -> PurchaseOrder:
        self.db.add(row)
        return row

    def get_purchase_order(
        self, organization_id: str, po_id: str, *, for_update: bool = False
    ) -> PurchaseOrder | None:
        stmt = select(PurchaseOrder).where(
            PurchaseOrder.id == po_id, PurchaseOrder.organization_id == organization_id
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_purchase_orders(
        self,
        *,
        organization_id: str,
        status: str | None = None,
        vendor_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PurchaseOrder]:
        lim, off = _page(limit, offset)
        stmt = select(PurchaseOrder).where(PurchaseOrder.organization_id == organization_id)
        if status:
            stmt = stmt.where(PurchaseOrder.status == status)
        if vendor_id:
            stmt = stmt.where(PurchaseOrder.vendor_id == vendor_id)
        return list(self.db.scalars(stmt.order_by(PurchaseOrder.created_at.desc()).limit(lim).offset(off)).all())

    def count_purchase_orders(self, organization_id: str, *, statuses: tuple[str, ...]) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PurchaseOrder)
                .where(PurchaseOrder.organization_id == organization_id, PurchaseOrder.status.in_(statuses))
            )
            or 0
        )

    def add_purchase_order_line(self, row: PurchaseOrderLine) -> PurchaseOrderLine:
        self.db.add(row)
        return row

    def get_purchase_order_line(self, organization_id: str, line_id: str) -> PurchaseOrderLine | None:
        return self.db.scalars(
            select(PurchaseOrderLine).where(
                PurchaseOrderLine.id == line_id,
                PurchaseOrderLine.organization_id == organization_id,
            )
        ).first()

    def list_purchase_order_lines(self, *, organization_id: str, po_id: str) -> list[PurchaseOrderLine]:
        return list(
            self.db.scalars(
                select(PurchaseOrderLine).where(
                    PurchaseOrderLine.organization_id == organization_id,
                    PurchaseOrderLine.purchase_order_id == po_id,
                )
            ).all()
        )

    def add_receipt(self, row: Receipt) -> Receipt:
        self.db.add(row)
        return row

    def get_receipt(self, organization_id: str, receipt_id: str, *, for_update: bool = False) -> Receipt | None:
        stmt = select(Receipt).where(Receipt.id == receipt_id, Receipt.organization_id == organization_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).first()

    def list_receipts(
        self,
        *,
        organization_id: str,
        status: str | None = None,
        purchase_order_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Receipt]:
        lim, off = _page(limit, offset)
        stmt = select(Receipt).where(Receipt.organization_id == organization_id)
        if status:
            stmt = stmt.where(Receipt.status == status)
        if purchase_order_id:
            stmt = stmt.where(Receipt.purchase_order_id == purchase_order_id)
        return list(self.db.scalars(stmt.order_by(Receipt.created_at.desc()).limit(lim).offset(off)).all())

    def add_receipt_line(self, row: ReceiptLine) -> ReceiptLine:
        self.db.add(row)
        return row

    def list_receipt_lines(self, *, organization_id: str, receipt_id: str) -> list[ReceiptLine]:
        return list(
            self.db.scalars(
                select(ReceiptLine).where(
                    ReceiptLine.organization_id == organization_id,
                    ReceiptLine.receipt_id == receipt_id,
                )
            ).all()
        )

    def add_vendor_invoice(self, row: VendorInvoice) -> VendorInvoice:
        self.db.add(row)
        return row

    def list_vendor_invoices(
        self, *, organization_id: str, purchase_order_id: str | None = None, limit: int = 100
    ) -> list[VendorInvoice]:
        lim, _ = _page(limit, 0)
        stmt = select(VendorInvoice).where(VendorInvoice.organization_id == organization_id)
        if purchase_order_id:
            stmt = stmt.where(VendorInvoice.purchase_order_id == purchase_order_id)
        return list(self.db.scalars(stmt.order_by(VendorInvoice.created_at.desc()).limit(lim)).all())

    # ------------------------------------------------------------------
    # Shipments
    # ------------------------------------------------------------------
    def add_shipment(self, row: Shipment) -> Shipment:
        self.db.add(row)
        return row

    def get_shipment(self, organization_id: str, shipment_id: str) -> Shipment | None:
        return self.db.scalars(
            select(Shipment).where(Shipment.id == shipment_id, Shipment.organization_id == organization_id)
        ).first()

    def list_shipments(
        self,
        *,
        organization_id: str,
        direction: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Shipment]:
        lim, off = _page(limit, offset)
        stmt = select(Shipment).where(Shipment.organization_id == organization_id)
        if direction:
            stmt = stmt.where(Shipment.direction == direction)
        if status:
            stmt = stmt.where(Shipment.status == status)
        return list(self.db.scalars(stmt.order_by(Shipment.created_at.desc()).limit(lim).offset(off)).all())

    def count_shipments(self, organization_id: str, *, status: str = "in_transit") -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(Shipment)
                .where(Shipment.organization_id == organization_id, Shipment.status == status)
            )
            or 0
        )
