"""Program B – Enterprise Logistics API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)

CONDITION_PATTERN = "^(serviceable|unserviceable|repair|scrap|quarantine|installed|loaned|pooled)$"
BALANCE_CONDITION_PATTERN = "^(serviceable|unserviceable|quarantine)$"
LOCATION_TYPE_PATTERN = "^(general|quarantine|receiving|shipping|hazmat|bonded|virtual)$"


# ---------------------------------------------------------------------------
# Warehouse & locations
# ---------------------------------------------------------------------------


class WarehouseCreate(BaseModel):
    organization_id: str | None = None
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    warehouse_type: str = Field(default="physical", pattern="^(physical|virtual|bonded)$")
    is_virtual: bool = False
    is_bonded: bool = False
    address: str = ""


class WarehouseOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    code: str
    name: str
    warehouse_type: str
    is_virtual: str
    is_bonded: str
    address: str
    status: str
    created_at: datetime
    updated_at: datetime


class WarehouseTreeCreate(BaseModel):
    """Create a warehouse plus its building/store/room/zone/aisle/shelf/bin chain."""

    organization_id: str | None = None
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    warehouse_type: str = Field(default="physical", pattern="^(physical|virtual|bonded)$")
    is_bonded: bool = False
    address: str = ""
    building_code: str = "BLD-1"
    store_code: str = "ST-1"
    room_code: str = "RM-1"
    zone_types: list[str] = Field(default_factory=lambda: ["receiving", "quarantine", "hazmat", "shipping", "general"])
    bins_per_zone: int = Field(default=1, ge=1, le=50)


class WarehouseTreeOut(BaseModel):
    warehouse: WarehouseOut
    locations: list["LocationOut"]


class LocationCreate(BaseModel):
    organization_id: str | None = None
    warehouse_id: str
    location_code: str = Field(min_length=1, max_length=120)
    location_type: str = Field(default="general", pattern=LOCATION_TYPE_PATTERN)
    building_id: str | None = None
    store_id: str | None = None
    room_id: str | None = None
    zone_id: str | None = None
    aisle_id: str | None = None
    shelf_id: str | None = None
    bin_id: str | None = None


class LocationOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    warehouse_id: str
    building_id: str | None
    store_id: str | None
    room_id: str | None
    zone_id: str | None
    aisle_id: str | None
    shelf_id: str | None
    bin_id: str | None
    location_code: str
    location_type: str
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Part master
# ---------------------------------------------------------------------------


class PartMasterCreate(BaseModel):
    organization_id: str | None = None
    oem_part_number: str = Field(min_length=1, max_length=120)
    description: str = ""
    manufacturer: str = ""
    customer_part_number: str = ""
    catalog_item_id: str | None = None
    ata_chapter_id: str | None = None
    nsn: str = ""
    part_class: str = Field(default="consumable", pattern="^(consumable|rotable|expendable|tool_related)$")
    is_serialized: bool = False
    is_life_limited: bool = False
    weight_kg: Decimal | None = None
    length_mm: Decimal | None = None
    width_mm: Decimal | None = None
    height_mm: Decimal | None = None
    shelf_life_days: int | None = Field(default=None, ge=1)
    is_hazmat: bool = False
    is_dangerous_goods: bool = False
    is_rohs: bool = False
    issue_policy: str = Field(default="FEFO", pattern="^(FIFO|FEFO)$")
    min_stock: Decimal = Field(default=Decimal("0"), ge=0)
    max_stock: Decimal = Field(default=Decimal("0"), ge=0)
    reorder_point: Decimal = Field(default=Decimal("0"), ge=0)
    unit_of_measure: str = "EA"


class PartMasterUpdate(BaseModel):
    description: str | None = None
    manufacturer: str | None = None
    customer_part_number: str | None = None
    ata_chapter_id: str | None = None
    nsn: str | None = None
    part_class: str | None = Field(default=None, pattern="^(consumable|rotable|expendable|tool_related)$")
    shelf_life_days: int | None = Field(default=None, ge=1)
    issue_policy: str | None = Field(default=None, pattern="^(FIFO|FEFO)$")
    min_stock: Decimal | None = Field(default=None, ge=0)
    max_stock: Decimal | None = Field(default=None, ge=0)
    reorder_point: Decimal | None = Field(default=None, ge=0)
    unit_of_measure: str | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|obsolete)$")


class PartMasterOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    catalog_item_id: str | None
    manufacturer: str
    oem_part_number: str
    customer_part_number: str
    description: str
    ata_chapter_id: str | None
    nsn: str
    part_class: str
    is_serialized: str
    is_life_limited: str
    weight_kg: Decimal | None
    length_mm: Decimal | None
    width_mm: Decimal | None
    height_mm: Decimal | None
    shelf_life_days: int | None
    is_hazmat: str
    is_dangerous_goods: str
    is_rohs: str
    issue_policy: str
    min_stock: Decimal
    max_stock: Decimal
    reorder_point: Decimal
    unit_of_measure: str
    status: str
    created_at: datetime
    updated_at: datetime


class IdentifierCreate(BaseModel):
    identifier_type: str = Field(default="barcode", pattern="^(barcode|qr|rfid)$")
    value: str = Field(min_length=1, max_length=200)
    part_master_id: str | None = None
    stock_unit_id: str | None = None
    tool_id: str | None = None


class IdentifierOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    part_master_id: str | None
    stock_unit_id: str | None
    tool_id: str | None
    identifier_type: str
    value: str
    status: str
    created_at: datetime


class AttachmentCreate(BaseModel):
    attachment_type: str = Field(default="document", pattern="^(certificate|photo|document|other)$")
    title: str = ""
    uri: str = Field(min_length=1, max_length=500)
    content_type: str = ""


class AttachmentOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    part_master_id: str
    attachment_type: str
    title: str
    uri: str
    content_type: str
    created_at: datetime


class FamilyCreate(BaseModel):
    organization_id: str | None = None
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    part_master_ids: list[str] = Field(default_factory=list)


class FamilyOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    code: str
    name: str
    status: str
    created_at: datetime


class FamilyMemberOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    family_id: str
    part_master_id: str


class SupersessionCreate(BaseModel):
    from_part_id: str
    to_part_id: str
    relation_type: str = Field(default="supersedes", pattern="^(supersedes|interchangeable|alternate)$")
    notes: str = ""


class SupersessionOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    from_part_id: str
    to_part_id: str
    relation_type: str
    notes: str
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------


class StockBalanceOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    part_master_id: str
    location_id: str
    condition: str
    qty_on_hand: Decimal
    qty_reserved: Decimal
    updated_at: datetime


class StockBalanceDetailOut(StockBalanceOut):
    part_number: str = ""
    part_description: str = ""
    location_code: str = ""
    qty_available: Decimal = Decimal("0")


class StockUnitOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    part_master_id: str
    serialized_component_id: str | None
    serial_number: str
    batch_number: str
    lot_number: str
    tsn_hours: Decimal
    tso_hours: Decimal
    csn_cycles: int
    cso_cycles: int
    location_id: str | None
    warehouse_id: str | None
    current_aircraft_id: str | None
    condition: str
    qty: Decimal
    received_at: datetime | None
    expires_at: datetime | None
    is_pool: str
    is_loan: str
    is_rental: str
    warranty_expires_at: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime


class StockMovementOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    movement_type: str
    part_master_id: str
    stock_unit_id: str | None
    from_location_id: str | None
    to_location_id: str | None
    qty: Decimal
    condition: str
    reference_type: str
    reference_id: str
    notes: str
    performed_by: str
    created_at: datetime


class ReceiveStockRequest(BaseModel):
    organization_id: str | None = None
    part_master_id: str
    location_id: str
    qty: Decimal = Field(gt=0)
    condition: str = Field(default="serviceable", pattern=BALANCE_CONDITION_PATTERN)
    serial_number: str = ""
    batch_number: str = ""
    lot_number: str = ""
    expires_at: datetime | None = None
    warranty_expires_at: datetime | None = None
    reference_type: str = ""
    reference_id: str = ""
    notes: str = ""


class IssueStockRequest(BaseModel):
    organization_id: str | None = None
    part_master_id: str
    qty: Decimal = Field(gt=0)
    location_id: str | None = None
    condition: str = Field(default="serviceable", pattern=BALANCE_CONDITION_PATTERN)
    reservation_id: str | None = None
    reference_type: str = ""
    reference_id: str = ""
    notes: str = ""


class AdjustStockRequest(BaseModel):
    organization_id: str | None = None
    part_master_id: str
    location_id: str
    qty_delta: Decimal
    condition: str = Field(default="serviceable", pattern=BALANCE_CONDITION_PATTERN)
    reason: str = Field(min_length=1, max_length=400)


class BulkAdjustRequest(BaseModel):
    organization_id: str | None = None
    reason: str = Field(min_length=1, max_length=400)
    lines: list[AdjustStockRequest] = Field(min_length=1)


class BulkAdjustResultLine(BaseModel):
    part_master_id: str
    location_id: str
    condition: str
    qty_delta: Decimal
    qty_on_hand: Decimal
    applied: bool
    message: str = ""


class BulkAdjustResult(BaseModel):
    applied: int
    rejected: int
    lines: list[BulkAdjustResultLine]


class ScrapStockRequest(BaseModel):
    organization_id: str | None = None
    part_master_id: str
    location_id: str
    qty: Decimal = Field(gt=0)
    condition: str = Field(default="serviceable", pattern=BALANCE_CONDITION_PATTERN)
    stock_unit_id: str | None = None
    reason: str = Field(min_length=1, max_length=400)


class ReservationCreate(BaseModel):
    organization_id: str | None = None
    part_master_id: str
    qty: Decimal = Field(default=Decimal("1"), gt=0)
    location_id: str | None = None
    stock_unit_id: str | None = None
    source_type: str = Field(default="manual", pattern="^(work_package|material_request|tool_plan|manual)$")
    source_id: str = ""
    parts_plan_line_id: str | None = None


class ReservationOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    part_master_id: str
    location_id: str | None
    stock_unit_id: str | None
    qty: Decimal
    status: str
    source_type: str
    source_id: str
    parts_plan_line_id: str | None
    created_by: str
    created_at: datetime
    released_at: datetime | None


class TransferCreate(BaseModel):
    organization_id: str | None = None
    from_warehouse_id: str
    to_warehouse_id: str
    from_location_id: str | None = None
    to_location_id: str | None = None
    notes: str = ""
    lines: list["TransferLineCreate"] = Field(default_factory=list)


class TransferLineCreate(BaseModel):
    part_master_id: str
    qty: Decimal = Field(default=Decimal("1"), gt=0)
    stock_unit_id: str | None = None


class TransferLineOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    transfer_id: str
    part_master_id: str
    stock_unit_id: str | None
    qty: Decimal
    status: str


class TransferOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    transfer_number: str
    from_warehouse_id: str
    to_warehouse_id: str
    from_location_id: str | None
    to_location_id: str | None
    status: str
    notes: str
    created_by: str
    created_at: datetime
    completed_at: datetime | None


class TransferDetailOut(TransferOut):
    lines: list[TransferLineOut] = Field(default_factory=list)


class TransferCompleteRequest(BaseModel):
    to_location_id: str | None = None
    notes: str = ""


class RotableCycleCreate(BaseModel):
    stock_unit_id: str
    cycle_type: str = Field(pattern="^(repair|core_return|exchange|loan|rental|pool|warranty)$")
    vendor_id: str | None = None
    warranty_claim: bool = False
    notes: str = ""


class RotableCycleCloseRequest(BaseModel):
    condition: str = Field(default="serviceable", pattern=CONDITION_PATTERN)
    notes: str = ""


class RotableCycleOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    stock_unit_id: str
    cycle_type: str
    vendor_id: str | None
    status: str
    warranty_claim: str
    notes: str
    opened_at: datetime
    closed_at: datetime | None
    created_by: str


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class ToolCreate(BaseModel):
    organization_id: str | None = None
    tool_code: str = Field(min_length=1, max_length=80)
    description: str = ""
    serial_number: str = ""
    location_id: str | None = None
    calibration_required: bool = True
    calibration_due_at: datetime | None = None
    certificate_uri: str = ""


class ToolUpdate(BaseModel):
    description: str | None = None
    serial_number: str | None = None
    location_id: str | None = None
    calibration_required: bool | None = None
    calibration_due_at: datetime | None = None
    certificate_uri: str | None = None
    status: str | None = Field(
        default=None, pattern="^(available|reserved|issued|missing|calibration_due|retired)$"
    )


class ToolOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    tool_code: str
    description: str
    serial_number: str
    location_id: str | None
    status: str
    calibration_required: str
    calibration_due_at: datetime | None
    calibration_status: str
    certificate_uri: str
    created_at: datetime
    updated_at: datetime


class ToolCalibrateRequest(BaseModel):
    calibrated_at: datetime | None = None
    due_at: datetime | None = None
    interval_days: int = Field(default=365, ge=1, le=3650)
    certificate_number: str = ""
    certificate_uri: str = ""
    notes: str = ""


class ToolCalibrationOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    tool_id: str
    calibrated_at: datetime
    due_at: datetime | None
    certificate_number: str
    certificate_uri: str
    performed_by: str
    notes: str
    created_at: datetime


class ToolIssueRequest(BaseModel):
    issued_to: str = Field(min_length=1, max_length=120)
    work_package_id: str | None = None


class ToolIssueOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    tool_id: str
    issued_to: str
    work_package_id: str | None
    status: str
    issued_at: datetime
    returned_at: datetime | None
    issued_by: str


class ToolReserveRequest(BaseModel):
    work_package_id: str | None = None
    tool_plan_line_id: str | None = None


class ToolReservationOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    tool_id: str
    work_package_id: str | None
    tool_plan_line_id: str | None
    status: str
    created_by: str
    created_at: datetime


class LostToolReportCreate(BaseModel):
    aircraft_id: str | None = None
    description: str = Field(min_length=1)


class LostToolReportOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    tool_id: str
    reported_by: str
    aircraft_id: str | None
    description: str
    status: str
    created_at: datetime


class ToolHistoryOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    tool_id: str
    event_type: str
    details: str
    performed_by: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Material requests
# ---------------------------------------------------------------------------


class MaterialRequestLineCreate(BaseModel):
    part_master_id: str
    qty_requested: Decimal = Field(default=Decimal("1"), gt=0)


class MaterialRequestCreate(BaseModel):
    organization_id: str | None = None
    work_order_id: str | None = None
    work_package_id: str | None = None
    job_card_id: str | None = None
    notes: str = ""
    lines: list[MaterialRequestLineCreate] = Field(min_length=1)


class MaterialRequestLineOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    material_request_id: str
    part_master_id: str
    qty_requested: Decimal
    qty_reserved: Decimal
    qty_issued: Decimal
    qty_returned: Decimal
    status: str


class MaterialRequestOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    request_number: str
    work_order_id: str | None
    work_package_id: str | None
    job_card_id: str | None
    requested_by: str
    approved_by: str
    status: str
    notes: str
    created_at: datetime
    updated_at: datetime


class MaterialRequestDetailOut(MaterialRequestOut):
    lines: list[MaterialRequestLineOut] = Field(default_factory=list)


class MaterialRequestIssueRequest(BaseModel):
    location_id: str | None = None
    notes: str = ""


class MaterialRequestReturnLine(BaseModel):
    line_id: str
    qty: Decimal = Field(gt=0)
    condition: str = Field(default="serviceable", pattern=BALANCE_CONDITION_PATTERN)


class MaterialRequestReturnRequest(BaseModel):
    location_id: str
    lines: list[MaterialRequestReturnLine] = Field(min_length=1)
    notes: str = ""


# ---------------------------------------------------------------------------
# Vendors & purchasing
# ---------------------------------------------------------------------------


class VendorCreate(BaseModel):
    organization_id: str | None = None
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    vendor_type: str = Field(default="distributor", pattern="^(oem|distributor|local|repair)$")
    certificates: str = ""
    approvals: str = ""
    contacts: str = ""
    rating: Decimal = Field(default=Decimal("0"), ge=0, le=5)
    lead_time_days: int = Field(default=14, ge=0, le=3650)
    performance_score: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    warranty_terms: str = ""
    repair_capability: bool = False


class VendorUpdate(BaseModel):
    name: str | None = None
    vendor_type: str | None = Field(default=None, pattern="^(oem|distributor|local|repair)$")
    certificates: str | None = None
    approvals: str | None = None
    contacts: str | None = None
    rating: Decimal | None = Field(default=None, ge=0, le=5)
    lead_time_days: int | None = Field(default=None, ge=0, le=3650)
    performance_score: Decimal | None = Field(default=None, ge=0, le=100)
    warranty_terms: str | None = None
    repair_capability: bool | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|blocked)$")


class VendorOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    code: str
    name: str
    vendor_type: str
    certificates: str
    approvals: str
    contacts: str
    rating: Decimal
    lead_time_days: int
    performance_score: Decimal
    warranty_terms: str
    repair_capability: str
    status: str
    created_at: datetime
    updated_at: datetime


class PurchaseRequestLineCreate(BaseModel):
    part_master_id: str
    qty: Decimal = Field(default=Decimal("1"), gt=0)
    needed_by: datetime | None = None


class PurchaseRequestCreate(BaseModel):
    organization_id: str | None = None
    work_package_id: str | None = None
    notes: str = ""
    lines: list[PurchaseRequestLineCreate] = Field(min_length=1)


class PurchaseRequestLineOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    purchase_request_id: str
    part_master_id: str
    qty: Decimal
    needed_by: datetime | None
    status: str


class PurchaseRequestOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    request_number: str
    status: str
    requested_by: str
    approved_by: str
    work_package_id: str | None
    notes: str
    created_at: datetime
    updated_at: datetime


class PurchaseRequestDetailOut(PurchaseRequestOut):
    lines: list[PurchaseRequestLineOut] = Field(default_factory=list)


class RfqOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    rfq_number: str
    purchase_request_id: str
    status: str
    created_at: datetime


class RfqQuoteCreate(BaseModel):
    vendor_id: str
    currency: str = Field(default="USD", max_length=10)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    lead_time_days: int = Field(default=14, ge=0, le=3650)
    notes: str = ""


class RfqQuoteOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    rfq_id: str
    vendor_id: str
    currency: str
    unit_price: Decimal
    lead_time_days: int
    selected: str
    notes: str
    created_at: datetime


class RfqDetailOut(RfqOut):
    quotes: list[RfqQuoteOut] = Field(default_factory=list)


class PurchaseOrderCreateFromRfq(BaseModel):
    expected_delivery: datetime | None = None
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    shipping_amount: Decimal = Field(default=Decimal("0"), ge=0)
    warranty_terms: str = ""
    notes: str = ""


class PurchaseOrderLineOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    purchase_order_id: str
    part_master_id: str
    qty_ordered: Decimal
    qty_received: Decimal
    qty_backordered: Decimal
    unit_price: Decimal
    status: str


class PurchaseOrderOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    po_number: str
    vendor_id: str
    purchase_request_id: str | None
    currency: str
    tax_amount: Decimal
    shipping_amount: Decimal
    expected_delivery: datetime | None
    status: str
    warranty_terms: str
    notes: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class PurchaseOrderDetailOut(PurchaseOrderOut):
    lines: list[PurchaseOrderLineOut] = Field(default_factory=list)


class ReceiptLineCreate(BaseModel):
    purchase_order_line_id: str | None = None
    part_master_id: str | None = None
    qty: Decimal = Field(gt=0)
    serial_number: str = ""
    batch_number: str = ""
    lot_number: str = ""
    expires_at: datetime | None = None


class ReceiptCreate(BaseModel):
    organization_id: str | None = None
    purchase_order_id: str | None = None
    shipment_id: str | None = None
    location_id: str | None = None
    lines: list[ReceiptLineCreate] = Field(min_length=1)


class ReceiptLineOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    receipt_id: str
    purchase_order_line_id: str | None
    part_master_id: str
    qty: Decimal
    serial_number: str
    batch_number: str
    lot_number: str
    expires_at: datetime | None
    inspection_status: str


class ReceiptOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    receipt_number: str
    purchase_order_id: str | None
    shipment_id: str | None
    location_id: str | None
    status: str
    received_by: str
    created_at: datetime


class ReceiptDetailOut(ReceiptOut):
    lines: list[ReceiptLineOut] = Field(default_factory=list)


class ReceiptInspectLine(BaseModel):
    line_id: str
    accept: bool = True
    notes: str = ""


class ReceiptInspectRequest(BaseModel):
    lines: list[ReceiptInspectLine] = Field(min_length=1)


class ReceiptPutawayRequest(BaseModel):
    location_id: str | None = None
    quarantine_location_id: str | None = None
    notes: str = ""


class VendorInvoiceCreate(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="USD", max_length=10)


class VendorInvoiceOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    invoice_number: str
    purchase_order_id: str
    vendor_id: str
    amount: Decimal
    currency: str
    status: str
    created_at: datetime


class ShipmentCreate(BaseModel):
    organization_id: str | None = None
    direction: str = Field(pattern="^(incoming|outgoing)$")
    courier: str = ""
    tracking_number: str = ""
    packing_list: str = ""
    is_export: bool = False
    is_import: bool = False
    is_dangerous_goods: bool = False
    purchase_order_id: str | None = None
    transfer_id: str | None = None


class ShipmentOut(BaseModel):
    model_config = ORM

    id: str
    organization_id: str
    shipment_number: str
    direction: str
    courier: str
    tracking_number: str
    packing_list: str
    is_export: str
    is_import: str
    is_dangerous_goods: str
    purchase_order_id: str | None
    transfer_id: str | None
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Scanning, dashboard, planning integration
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    organization_id: str | None = None
    value: str = Field(min_length=1, max_length=200)
    identifier_type: str | None = Field(default=None, pattern="^(barcode|qr|rfid)$")


class ScanOut(BaseModel):
    value: str
    identifier_type: str
    resolved: bool
    target_type: str  # part | stock_unit | tool | unknown
    target_id: str
    title: str
    subtitle: str = ""
    part: PartMasterOut | None = None
    stock_unit: StockUnitOut | None = None
    tool: ToolOut | None = None
    balances: list[StockBalanceDetailOut] = Field(default_factory=list)


class DashboardOut(BaseModel):
    organization_id: str
    generated_at: datetime
    warehouses: int
    locations: int
    parts: int
    stock_lines: int
    total_on_hand: Decimal
    total_reserved: Decimal
    low_stock_parts: int
    expiring_lots_30d: int
    expired_lots: int
    quarantine_lines: int
    open_reservations: int
    movements_today: int
    open_material_requests: int
    open_purchase_requests: int
    open_purchase_orders: int
    shipments_in_transit: int
    open_rotable_cycles: int
    tools_total: int
    tools_issued: int
    tools_calibration_due_30d: int
    tools_missing: int
    open_lost_tool_reports: int


class ShortageItemOut(BaseModel):
    part_master_id: str
    oem_part_number: str
    description: str
    part_class: str
    qty_available: Decimal
    reorder_point: Decimal
    min_stock: Decimal
    status: str  # low_stock | no_stock


class ShortagesOut(BaseModel):
    organization_id: str
    items: list[ShortageItemOut]


class MaterialPlanningRequest(BaseModel):
    work_package_id: str | None = None
    auto_purchase_request: bool = True
    lines: list[dict[str, object]] = Field(default_factory=list)


class ToolPlanningRequest(BaseModel):
    work_package_id: str | None = None
    lines: list[dict[str, object]] = Field(default_factory=list)


class MaterialPlanningLineResult(BaseModel):
    parts_plan_line_id: str
    part_number: str
    part_master_id: str | None = None
    qty_required: Decimal
    qty_available: Decimal
    qty_reserved: Decimal
    status: str  # ok | shortage | purchase_required
    reservation_id: str | None = None
    purchase_request_id: str | None = None
    expected_delivery: datetime | None = None
    message: str = ""


class MaterialPlanningResult(BaseModel):
    organization_id: str
    work_package_id: str | None
    generated_at: datetime
    reserved_lines: int
    shortage_lines: int
    purchase_required_lines: int
    purchase_request_id: str | None = None
    lines: list[MaterialPlanningLineResult] = Field(default_factory=list)


class ToolPlanningLineResult(BaseModel):
    tool_plan_line_id: str
    tool_code: str
    tool_id: str | None = None
    status: str  # reserved | available | overdue_cal | unavailable
    calibration_status: str = ""
    calibration_expires_at: datetime | None = None
    reservation_id: str | None = None
    message: str = ""


class ToolPlanningResult(BaseModel):
    organization_id: str
    work_package_id: str | None
    generated_at: datetime
    reserved_lines: int
    unavailable_lines: int
    lines: list[ToolPlanningLineResult] = Field(default_factory=list)


class SeedDemoOut(BaseModel):
    organization_id: str
    created: bool
    warehouse_id: str
    location_ids: list[str] = Field(default_factory=list)
    part_ids: list[str] = Field(default_factory=list)
    tool_ids: list[str] = Field(default_factory=list)
    vendor_ids: list[str] = Field(default_factory=list)
    material_request_id: str | None = None
    message: str = ""


WarehouseTreeOut.model_rebuild()
TransferCreate.model_rebuild()
