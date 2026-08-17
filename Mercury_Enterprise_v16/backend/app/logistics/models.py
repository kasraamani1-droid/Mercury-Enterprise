"""Program B – Enterprise Logistics data model."""

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


# ---------------------------------------------------------------------------
# Warehouse hierarchy
# ---------------------------------------------------------------------------


class Warehouse(Base):
    __tablename__ = "logistics_warehouses"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(200))
    # physical | virtual | bonded
    warehouse_type: Mapped[str] = mapped_column(String(40), default="physical", index=True)
    is_virtual: Mapped[str] = mapped_column(String(10), default="false")
    is_bonded: Mapped[str] = mapped_column(String(10), default="false")
    address: Mapped[str] = mapped_column(String(400), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_log_wh_org_code"),)


class Building(Base):
    __tablename__ = "logistics_buildings"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("logistics_warehouses.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class StoreArea(Base):
    __tablename__ = "logistics_stores"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("logistics_buildings.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Room(Base):
    __tablename__ = "logistics_rooms"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("logistics_stores.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Zone(Base):
    __tablename__ = "logistics_zones"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("logistics_rooms.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200), default="")
    # general | quarantine | receiving | shipping | hazmat | bonded
    zone_type: Mapped[str] = mapped_column(String(40), default="general", index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Aisle(Base):
    __tablename__ = "logistics_aisles"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("logistics_zones.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Shelf(Base):
    __tablename__ = "logistics_shelves"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    aisle_id: Mapped[str] = mapped_column(ForeignKey("logistics_aisles.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Bin(Base):
    __tablename__ = "logistics_bins"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    shelf_id: Mapped[str] = mapped_column(ForeignKey("logistics_shelves.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Location(Base):
    """Denormalized pickable location (bin leaf or area)."""

    __tablename__ = "logistics_locations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("logistics_warehouses.id"), index=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_buildings.id"), nullable=True)
    store_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_stores.id"), nullable=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_rooms.id"), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_zones.id"), nullable=True)
    aisle_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_aisles.id"), nullable=True)
    shelf_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_shelves.id"), nullable=True)
    bin_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_bins.id"), nullable=True)
    location_code: Mapped[str] = mapped_column(String(120), index=True)
    # general | quarantine | receiving | shipping | hazmat | bonded | virtual
    location_type: Mapped[str] = mapped_column(String(40), default="general", index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "location_code", name="uq_log_loc_org_code"),
        Index("ix_log_loc_org_wh_type", "organization_id", "warehouse_id", "location_type"),
    )


class WarehouseTransfer(Base):
    __tablename__ = "logistics_warehouse_transfers"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    transfer_number: Mapped[str] = mapped_column(String(80), index=True)
    from_warehouse_id: Mapped[str] = mapped_column(ForeignKey("logistics_warehouses.id"), index=True)
    to_warehouse_id: Mapped[str] = mapped_column(ForeignKey("logistics_warehouses.id"), index=True)
    from_location_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_locations.id"), nullable=True)
    to_location_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_locations.id"), nullable=True)
    # draft | in_transit | completed | cancelled
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("organization_id", "transfer_number", name="uq_log_xfer_num"),)


# ---------------------------------------------------------------------------
# Part master
# ---------------------------------------------------------------------------


class PartMaster(Base):
    __tablename__ = "logistics_part_masters"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    catalog_item_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    manufacturer: Mapped[str] = mapped_column(String(200), default="")
    oem_part_number: Mapped[str] = mapped_column(String(120), index=True)
    customer_part_number: Mapped[str] = mapped_column(String(120), default="", index=True)
    description: Mapped[str] = mapped_column(String(400), default="")
    ata_chapter_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    nsn: Mapped[str] = mapped_column(String(80), default="", index=True)
    # consumable | rotable | expendable | tool_related
    part_class: Mapped[str] = mapped_column(String(40), default="consumable", index=True)
    is_serialized: Mapped[str] = mapped_column(String(10), default="false")
    is_life_limited: Mapped[str] = mapped_column(String(10), default="false")
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    length_mm: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    width_mm: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    height_mm: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_hazmat: Mapped[str] = mapped_column(String(10), default="false")
    is_dangerous_goods: Mapped[str] = mapped_column(String(10), default="false")
    is_rohs: Mapped[str] = mapped_column(String(10), default="false")
    issue_policy: Mapped[str] = mapped_column(String(20), default="FEFO")  # FIFO | FEFO
    min_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    max_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    unit_of_measure: Mapped[str] = mapped_column(String(20), default="EA")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "oem_part_number", name="uq_log_part_org_oem"),
        Index("ix_log_part_org_class", "organization_id", "part_class"),
    )


class PartFamily(Base):
    __tablename__ = "logistics_part_families"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_log_family_org_code"),)


class PartFamilyMember(Base):
    __tablename__ = "logistics_part_family_members"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    family_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_families.id"), index=True)
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)

    __table_args__ = (UniqueConstraint("family_id", "part_master_id", name="uq_log_family_member"),)


class PartSupersession(Base):
    __tablename__ = "logistics_part_supersessions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    from_part_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    to_part_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    # supersedes | interchangeable | alternate
    relation_type: Mapped[str] = mapped_column(String(40), default="supersedes", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("from_part_id", "to_part_id", "relation_type", name="uq_log_super"),)


class PartAttachment(Base):
    __tablename__ = "logistics_part_attachments"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    # certificate | photo | document | other
    attachment_type: Mapped[str] = mapped_column(String(40), default="document", index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    uri: Mapped[str] = mapped_column(String(500), default="")
    content_type: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------


class StockBalance(Base):
    __tablename__ = "logistics_stock_balances"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("logistics_locations.id"), index=True)
    # serviceable | unserviceable | quarantine
    condition: Mapped[str] = mapped_column(String(40), default="serviceable", index=True)
    qty_on_hand: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    qty_reserved: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("part_master_id", "location_id", "condition", name="uq_log_balance"),
        Index("ix_log_bal_org_part", "organization_id", "part_master_id"),
    )


class StockUnit(Base):
    """Serialized / lot-tracked inventory unit (rotable or batch)."""

    __tablename__ = "logistics_stock_units"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    serialized_component_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    serial_number: Mapped[str] = mapped_column(String(120), default="", index=True)
    batch_number: Mapped[str] = mapped_column(String(120), default="", index=True)
    lot_number: Mapped[str] = mapped_column(String(120), default="", index=True)
    tsn_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    tso_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    csn_cycles: Mapped[int] = mapped_column(Integer, default=0)
    cso_cycles: Mapped[int] = mapped_column(Integer, default=0)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_locations.id"), nullable=True, index=True)
    warehouse_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_warehouses.id"), nullable=True, index=True)
    current_aircraft_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    # serviceable | unserviceable | repair | scrap | quarantine | installed | loaned | pooled
    condition: Mapped[str] = mapped_column(String(40), default="serviceable", index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("1"))
    received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    is_pool: Mapped[str] = mapped_column(String(10), default="false")
    is_loan: Mapped[str] = mapped_column(String(10), default="false")
    is_rental: Mapped[str] = mapped_column(String(10), default="false")
    warranty_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        Index("ix_log_unit_org_serial", "organization_id", "serial_number"),
        Index("ix_log_unit_org_part_cond", "organization_id", "part_master_id", "condition"),
    )


class StockMovement(Base):
    """Immutable stock ledger entry."""

    __tablename__ = "logistics_stock_movements"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    # receive | issue | transfer | adjust | return | scrap | repair | loan | exchange | reservation | release
    movement_type: Mapped[str] = mapped_column(String(40), index=True)
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    stock_unit_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_stock_units.id"), nullable=True, index=True)
    from_location_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_locations.id"), nullable=True)
    to_location_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_locations.id"), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    condition: Mapped[str] = mapped_column(String(40), default="serviceable")
    reference_type: Mapped[str] = mapped_column(String(40), default="")  # mr | po | transfer | wo | adjust
    reference_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    performed_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_log_mov_org_created", "organization_id", "created_at"),)


class StockReservation(Base):
    __tablename__ = "logistics_reservations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_locations.id"), nullable=True)
    stock_unit_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_stock_units.id"), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("1"))
    # open | issued | released | cancelled
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    # work_package | material_request | tool_plan | manual
    source_type: Mapped[str] = mapped_column(String(40), default="manual", index=True)
    source_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    parts_plan_line_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_log_res_org_status", "organization_id", "status"),)


class WarehouseTransferLine(Base):
    __tablename__ = "logistics_warehouse_transfer_lines"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    transfer_id: Mapped[str] = mapped_column(ForeignKey("logistics_warehouse_transfers.id"), index=True)
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    stock_unit_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_stock_units.id"), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("1"))
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class Tool(Base):
    __tablename__ = "logistics_tools"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    tool_code: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(String(300), default="")
    serial_number: Mapped[str] = mapped_column(String(120), default="", index=True)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_locations.id"), nullable=True)
    # available | reserved | issued | missing | calibration_due | retired
    status: Mapped[str] = mapped_column(String(40), default="available", index=True)
    calibration_required: Mapped[str] = mapped_column(String(10), default="true")
    calibration_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    calibration_status: Mapped[str] = mapped_column(String(40), default="current", index=True)
    certificate_uri: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("organization_id", "tool_code", name="uq_log_tool_code"),)


class ToolKit(Base):
    __tablename__ = "logistics_tool_kits"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_log_kit_code"),)


class ToolKitMember(Base):
    __tablename__ = "logistics_tool_kit_members"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    kit_id: Mapped[str] = mapped_column(ForeignKey("logistics_tool_kits.id"), index=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("logistics_tools.id"), index=True)

    __table_args__ = (UniqueConstraint("kit_id", "tool_id", name="uq_log_kit_member"),)


class ShadowBoard(Base):
    __tablename__ = "logistics_shadow_boards"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    hangar_bay: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ToolCalibration(Base):
    __tablename__ = "logistics_tool_calibrations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("logistics_tools.id"), index=True)
    calibrated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    certificate_number: Mapped[str] = mapped_column(String(120), default="")
    certificate_uri: Mapped[str] = mapped_column(String(500), default="")
    performed_by: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ToolIssue(Base):
    __tablename__ = "logistics_tool_issues"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("logistics_tools.id"), index=True)
    issued_to: Mapped[str] = mapped_column(String(120), default="")
    work_package_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    # issued | returned | lost
    status: Mapped[str] = mapped_column(String(40), default="issued", index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    issued_by: Mapped[str] = mapped_column(String(120), default="")


class ToolReservation(Base):
    __tablename__ = "logistics_tool_reservations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("logistics_tools.id"), index=True)
    work_package_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    tool_plan_line_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class LostToolReport(Base):
    __tablename__ = "logistics_lost_tool_reports"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("logistics_tools.id"), index=True)
    reported_by: Mapped[str] = mapped_column(String(120), default="")
    aircraft_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # open | found | closed
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ToolHistory(Base):
    __tablename__ = "logistics_tool_history"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("logistics_tools.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    details: Mapped[str] = mapped_column(Text, default="")
    performed_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PartIdentifier(Base):
    __tablename__ = "logistics_part_identifiers"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    part_master_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_part_masters.id"), nullable=True, index=True)
    stock_unit_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_stock_units.id"), nullable=True, index=True)
    tool_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_tools.id"), nullable=True, index=True)
    # barcode | qr | rfid
    identifier_type: Mapped[str] = mapped_column(String(20), index=True)
    value: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "identifier_type", "value", name="uq_log_identifier"),
    )


# ---------------------------------------------------------------------------
# Material requests
# ---------------------------------------------------------------------------


class MaterialRequest(Base):
    __tablename__ = "logistics_material_requests"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    request_number: Mapped[str] = mapped_column(String(80), index=True)
    work_order_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    work_package_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    job_card_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    requested_by: Mapped[str] = mapped_column(String(120), default="")
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    # requested | approved | reserved | issued | returned | cancelled
    status: Mapped[str] = mapped_column(String(40), default="requested", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "request_number", name="uq_log_mr_num"),)


class MaterialRequestLine(Base):
    __tablename__ = "logistics_material_request_lines"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    material_request_id: Mapped[str] = mapped_column(ForeignKey("logistics_material_requests.id"), index=True)
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    qty_requested: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("1"))
    qty_reserved: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    qty_issued: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    qty_returned: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(40), default="requested", index=True)


# ---------------------------------------------------------------------------
# Vendors & purchasing
# ---------------------------------------------------------------------------


class Vendor(Base):
    __tablename__ = "logistics_vendors"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    # oem | distributor | local | repair
    vendor_type: Mapped[str] = mapped_column(String(40), default="distributor", index=True)
    certificates: Mapped[str] = mapped_column(Text, default="")
    approvals: Mapped[str] = mapped_column(Text, default="")
    contacts: Mapped[str] = mapped_column(Text, default="")
    rating: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0"))
    lead_time_days: Mapped[int] = mapped_column(Integer, default=14)
    performance_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    warranty_terms: Mapped[str] = mapped_column(String(300), default="")
    repair_capability: Mapped[str] = mapped_column(String(10), default="false")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_log_vendor_code"),)


class RotableCycle(Base):
    __tablename__ = "logistics_rotable_cycles"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    stock_unit_id: Mapped[str] = mapped_column(ForeignKey("logistics_stock_units.id"), index=True)
    # repair | core_return | exchange | loan | rental | pool | warranty
    cycle_type: Mapped[str] = mapped_column(String(40), index=True)
    vendor_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_vendors.id"), nullable=True, index=True)
    # open | in_repair | closed | cancelled
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    warranty_claim: Mapped[str] = mapped_column(String(10), default="false")
    notes: Mapped[str] = mapped_column(Text, default="")
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), default="")


class PurchaseRequest(Base):
    __tablename__ = "logistics_purchase_requests"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    request_number: Mapped[str] = mapped_column(String(80), index=True)
    # draft | approved | rfq | po_created | cancelled
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    requested_by: Mapped[str] = mapped_column(String(120), default="")
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    work_package_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "request_number", name="uq_log_pr_num"),)


class PurchaseRequestLine(Base):
    __tablename__ = "logistics_purchase_request_lines"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    purchase_request_id: Mapped[str] = mapped_column(ForeignKey("logistics_purchase_requests.id"), index=True)
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("1"))
    needed_by: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)


class Rfq(Base):
    __tablename__ = "logistics_rfqs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    rfq_number: Mapped[str] = mapped_column(String(80), index=True)
    purchase_request_id: Mapped[str] = mapped_column(ForeignKey("logistics_purchase_requests.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "rfq_number", name="uq_log_rfq_num"),)


class RfqQuote(Base):
    __tablename__ = "logistics_rfq_quotes"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    rfq_id: Mapped[str] = mapped_column(ForeignKey("logistics_rfqs.id"), index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("logistics_vendors.id"), index=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    lead_time_days: Mapped[int] = mapped_column(Integer, default=14)
    selected: Mapped[str] = mapped_column(String(10), default="false")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PurchaseOrder(Base):
    __tablename__ = "logistics_purchase_orders"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    po_number: Mapped[str] = mapped_column(String(80), index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("logistics_vendors.id"), index=True)
    purchase_request_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_purchase_requests.id"), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    expected_delivery: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # open | partial | received | closed | cancelled | returned
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    warranty_terms: Mapped[str] = mapped_column(String(300), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("organization_id", "po_number", name="uq_log_po_num"),)


class PurchaseOrderLine(Base):
    __tablename__ = "logistics_purchase_order_lines"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    purchase_order_id: Mapped[str] = mapped_column(ForeignKey("logistics_purchase_orders.id"), index=True)
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    qty_ordered: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("1"))
    qty_received: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    qty_backordered: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)


class Shipment(Base):
    __tablename__ = "logistics_shipments"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    shipment_number: Mapped[str] = mapped_column(String(80), index=True)
    # incoming | outgoing
    direction: Mapped[str] = mapped_column(String(20), index=True)
    courier: Mapped[str] = mapped_column(String(120), default="")
    tracking_number: Mapped[str] = mapped_column(String(120), default="", index=True)
    packing_list: Mapped[str] = mapped_column(Text, default="")
    is_export: Mapped[str] = mapped_column(String(10), default="false")
    is_import: Mapped[str] = mapped_column(String(10), default="false")
    is_dangerous_goods: Mapped[str] = mapped_column(String(10), default="false")
    purchase_order_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    transfer_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="in_transit", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "shipment_number", name="uq_log_ship_num"),)


class Receipt(Base):
    __tablename__ = "logistics_receipts"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    receipt_number: Mapped[str] = mapped_column(String(80), index=True)
    purchase_order_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_purchase_orders.id"), nullable=True, index=True)
    shipment_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_shipments.id"), nullable=True)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("logistics_locations.id"), nullable=True)
    # receiving | inspection | putaway | closed
    status: Mapped[str] = mapped_column(String(40), default="receiving", index=True)
    received_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "receipt_number", name="uq_log_rcpt_num"),)


class ReceiptLine(Base):
    __tablename__ = "logistics_receipt_lines"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("logistics_receipts.id"), index=True)
    purchase_order_line_id: Mapped[str | None] = mapped_column(
        ForeignKey("logistics_purchase_order_lines.id"), nullable=True
    )
    part_master_id: Mapped[str] = mapped_column(ForeignKey("logistics_part_masters.id"), index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("1"))
    serial_number: Mapped[str] = mapped_column(String(120), default="")
    batch_number: Mapped[str] = mapped_column(String(120), default="")
    lot_number: Mapped[str] = mapped_column(String(120), default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # pending | accepted | rejected
    inspection_status: Mapped[str] = mapped_column(String(40), default="pending", index=True)


class VendorInvoice(Base):
    __tablename__ = "logistics_vendor_invoices"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    invoice_number: Mapped[str] = mapped_column(String(80), index=True)
    purchase_order_id: Mapped[str] = mapped_column(ForeignKey("logistics_purchase_orders.id"), index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("logistics_vendors.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("organization_id", "invoice_number", name="uq_log_inv_num"),)
