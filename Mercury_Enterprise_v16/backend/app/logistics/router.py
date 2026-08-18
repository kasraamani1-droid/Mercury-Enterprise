"""Program B – Enterprise Logistics HTTP API."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..database import get_db
from ..security.runtime_authz import require_allowed
from .schemas import (
    AdjustStockRequest,
    AttachmentCreate,
    AttachmentOut,
    BulkAdjustRequest,
    BulkAdjustResult,
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
    MaterialRequestCreate,
    MaterialRequestDetailOut,
    MaterialRequestIssueRequest,
    MaterialRequestOut,
    MaterialRequestReturnRequest,
    PartMasterCreate,
    PartMasterOut,
    PartMasterUpdate,
    PurchaseOrderCreateFromRfq,
    PurchaseOrderDetailOut,
    PurchaseOrderOut,
    PurchaseRequestCreate,
    PurchaseRequestDetailOut,
    PurchaseRequestOut,
    ReceiptCreate,
    ReceiptDetailOut,
    ReceiptInspectRequest,
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
    ToolReservationOut,
    ToolReserveRequest,
    ToolUpdate,
    TransferCompleteRequest,
    TransferCreate,
    TransferDetailOut,
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
    MaterialPlanningRequest,
    MaterialPlanningResult,
    ToolPlanningRequest,
    ToolPlanningResult,
)
from .service import ActorContext, LogisticsService

logger = logging.getLogger("mercury.logistics")
router = APIRouter(prefix="/api/v1/logistics", tags=["logistics"])

Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_logistics_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("logistics.read", "store.read", "planning.read", "maintenance.read", "work_order.read"),
        any_of=True,
        detail="Logistics read required",
    )
    return session


def require_logistics_manage(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("logistics.manage", "store.manage", "maintenance.manage", "work_order.manage"),
        any_of=True,
        detail="Logistics manage required",
    )
    return session


def require_logistics_stores(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("logistics.stores", "store.manage", "logistics.manage", "maintenance.manage", "work_order.manage"),
        any_of=True,
        detail="Stores permission required",
    )
    return session


def require_logistics_purchase(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("logistics.purchase", "procurement.manage", "logistics.manage", "maintenance.manage"),
        any_of=True,
        detail="Purchasing permission required",
    )
    return session


def require_logistics_tools(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("logistics.tools", "store.manage", "logistics.manage", "maintenance.manage", "work_order.manage"),
        any_of=True,
        detail="Tool store permission required",
    )
    return session


def _svc(db: Session) -> LogisticsService:
    return LogisticsService(db)


def _actor(session: Session_) -> ActorContext:
    return ActorContext(
        username=str(session["operator"]),
        role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )


def _audit(
    db: Session,
    session: Session_,
    *,
    action: str,
    target_type: str,
    target_id: str,
    details: str = "",
    organization_id: str | None = None,
) -> None:
    """Route-level audit trail mirroring the planning module."""
    try:
        record_audit(
            db,
            action=action,
            actor=str(session["operator"]),
            actor_role=str(session["role"]),
            organization_id=organization_id or str(session["organization_id"]),
            site_id=str(session["site_id"]),
            target_type=target_type,
            target_id=target_id,
            source="api",
            outcome="success",
            origin="operator",
            details=details,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("logistics audit failed action=%s target=%s", action, target_id)


# ---------------------------------------------------------------------------
# Warehouses & locations
# ---------------------------------------------------------------------------


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(
    organization_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[WarehouseOut]:
    return _svc(db).list_warehouses(_actor(session), organization_id=organization_id, limit=limit, offset=offset)


@router.post("/warehouses", response_model=WarehouseOut, status_code=201)
def create_warehouse(
    payload: WarehouseCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> WarehouseOut:
    out = _svc(db).create_warehouse(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.warehouse.create",
        target_type="logistics_warehouse",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"code={out.code}",
    )
    return out


@router.post("/warehouses/tree", response_model=WarehouseTreeOut, status_code=201)
def create_warehouse_tree(
    payload: WarehouseTreeCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> WarehouseTreeOut:
    out = _svc(db).create_warehouse_tree(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.warehouse.tree.create",
        target_type="logistics_warehouse",
        target_id=out.warehouse.id,
        organization_id=out.warehouse.organization_id,
        details=f"locations={len(out.locations)}",
    )
    return out


@router.get("/locations", response_model=list[LocationOut])
def list_locations(
    organization_id: str | None = None,
    warehouse_id: str | None = None,
    location_type: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[LocationOut]:
    return _svc(db).list_locations(
        _actor(session),
        organization_id=organization_id,
        warehouse_id=warehouse_id,
        location_type=location_type,
        limit=limit,
        offset=offset,
    )


@router.post("/locations", response_model=LocationOut, status_code=201)
def create_location(
    payload: LocationCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> LocationOut:
    out = _svc(db).create_location(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.location.create",
        target_type="logistics_location",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"code={out.location_code}",
    )
    return out


# ---------------------------------------------------------------------------
# Part master
# ---------------------------------------------------------------------------


@router.get("/parts", response_model=list[PartMasterOut])
def list_parts(
    organization_id: str | None = None,
    q: str | None = None,
    part_class: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[PartMasterOut]:
    return _svc(db).list_parts(
        _actor(session),
        organization_id=organization_id,
        q=q,
        part_class=part_class,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post("/parts", response_model=PartMasterOut, status_code=201)
def create_part(
    payload: PartMasterCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> PartMasterOut:
    out = _svc(db).create_part(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.part.create",
        target_type="logistics_part_master",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"pn={out.oem_part_number}",
    )
    return out


@router.get("/parts/{part_id}", response_model=PartMasterOut)
def get_part(
    part_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> PartMasterOut:
    return _svc(db).get_part(part_id, _actor(session))


@router.put("/parts/{part_id}", response_model=PartMasterOut)
def update_part(
    part_id: str,
    payload: PartMasterUpdate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> PartMasterOut:
    out = _svc(db).update_part(part_id, payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.part.update",
        target_type="logistics_part_master",
        target_id=out.id,
        organization_id=out.organization_id,
    )
    return out


@router.get("/parts/{part_id}/identifiers", response_model=list[IdentifierOut])
def list_identifiers(
    part_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[IdentifierOut]:
    return _svc(db).list_identifiers(part_id, _actor(session))


@router.post("/identifiers", response_model=IdentifierOut, status_code=201)
def add_identifier(
    payload: IdentifierCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> IdentifierOut:
    out = _svc(db).add_identifier(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.identifier.create",
        target_type="logistics_part_identifier",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"type={out.identifier_type}",
    )
    return out


@router.get("/parts/{part_id}/attachments", response_model=list[AttachmentOut])
def list_attachments(
    part_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[AttachmentOut]:
    return _svc(db).list_attachments(part_id, _actor(session))


@router.post("/parts/{part_id}/attachments", response_model=AttachmentOut, status_code=201)
def add_attachment(
    part_id: str,
    payload: AttachmentCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> AttachmentOut:
    out = _svc(db).add_attachment(part_id, payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.part.attachment.create",
        target_type="logistics_part_attachment",
        target_id=out.id,
        organization_id=out.organization_id,
    )
    return out


@router.get("/families", response_model=list[FamilyOut])
def list_families(
    organization_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[FamilyOut]:
    return _svc(db).list_families(_actor(session), organization_id=organization_id, limit=limit, offset=offset)


@router.post("/families", response_model=FamilyOut, status_code=201)
def create_family(
    payload: FamilyCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> FamilyOut:
    out = _svc(db).create_family(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.family.create",
        target_type="logistics_part_family",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"code={out.code}",
    )
    return out


@router.get("/families/{family_id}/members", response_model=list[FamilyMemberOut])
def list_family_members(
    family_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[FamilyMemberOut]:
    return _svc(db).list_family_members(family_id, _actor(session))


@router.get("/supersessions", response_model=list[SupersessionOut])
def list_supersessions(
    organization_id: str | None = None,
    part_master_id: str | None = None,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[SupersessionOut]:
    return _svc(db).list_supersessions(
        _actor(session), organization_id=organization_id, part_master_id=part_master_id
    )


@router.post("/supersessions", response_model=SupersessionOut, status_code=201)
def add_supersession(
    payload: SupersessionCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> SupersessionOut:
    out = _svc(db).add_supersession(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.supersession.create",
        target_type="logistics_part_supersession",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"relation={out.relation_type}",
    )
    return out


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------


@router.get("/stock/balances", response_model=list[StockBalanceDetailOut])
def list_balances(
    organization_id: str | None = None,
    part_master_id: str | None = None,
    location_id: str | None = None,
    condition: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[StockBalanceDetailOut]:
    return _svc(db).list_balances(
        _actor(session),
        organization_id=organization_id,
        part_master_id=part_master_id,
        location_id=location_id,
        condition=condition,
        limit=limit,
        offset=offset,
    )


@router.get("/stock/units", response_model=list[StockUnitOut])
def list_stock_units(
    organization_id: str | None = None,
    part_master_id: str | None = None,
    location_id: str | None = None,
    condition: str | None = None,
    serial_number: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[StockUnitOut]:
    return _svc(db).list_stock_units(
        _actor(session),
        organization_id=organization_id,
        part_master_id=part_master_id,
        location_id=location_id,
        condition=condition,
        serial_number=serial_number,
        limit=limit,
        offset=offset,
    )


@router.get("/stock/movements", response_model=list[StockMovementOut])
def list_movements(
    organization_id: str | None = None,
    part_master_id: str | None = None,
    movement_type: str | None = None,
    reference_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[StockMovementOut]:
    return _svc(db).list_movements(
        _actor(session),
        organization_id=organization_id,
        part_master_id=part_master_id,
        movement_type=movement_type,
        reference_id=reference_id,
        limit=limit,
        offset=offset,
    )


@router.post("/stock/receive", response_model=StockUnitOut, status_code=201)
def receive_stock(
    payload: ReceiveStockRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> StockUnitOut:
    return _svc(db).receive_stock(payload, _actor(session))


@router.post("/stock/issue", response_model=list[StockMovementOut])
def issue_stock(
    payload: IssueStockRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> list[StockMovementOut]:
    return _svc(db).issue_stock(payload, _actor(session))


@router.post("/stock/adjust", response_model=StockBalanceDetailOut)
def adjust_stock(
    payload: AdjustStockRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> StockBalanceDetailOut:
    return _svc(db).adjust_stock(payload, _actor(session))


@router.post("/stock/bulk-adjust", response_model=BulkAdjustResult)
def bulk_adjust(
    payload: BulkAdjustRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> BulkAdjustResult:
    return _svc(db).bulk_adjust(payload, _actor(session))


@router.post("/stock/scrap", response_model=StockBalanceDetailOut)
def scrap_stock(
    payload: ScrapStockRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> StockBalanceDetailOut:
    return _svc(db).scrap_stock(payload, _actor(session))


@router.get("/reservations", response_model=list[ReservationOut])
def list_reservations(
    organization_id: str | None = None,
    status_filter: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    part_master_id: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[ReservationOut]:
    return _svc(db).list_reservations(
        _actor(session),
        organization_id=organization_id,
        status=status_filter,
        source_type=source_type,
        source_id=source_id,
        part_master_id=part_master_id,
        limit=limit,
        offset=offset,
    )


@router.post("/reservations", response_model=ReservationOut, status_code=201)
def reserve_stock(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> ReservationOut:
    out = _svc(db).reserve_stock(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.reservation.create",
        target_type="logistics_reservation",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"part={out.part_master_id};qty={out.qty}",
    )
    return out


@router.post("/reservations/{reservation_id}/release", response_model=ReservationOut)
def release_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> ReservationOut:
    out = _svc(db).release_reservation(reservation_id, _actor(session))
    _audit(
        db,
        session,
        action="logistics.reservation.release",
        target_type="logistics_reservation",
        target_id=out.id,
        organization_id=out.organization_id,
    )
    return out


# ---------------------------------------------------------------------------
# Transfers & rotable cycles
# ---------------------------------------------------------------------------


@router.get("/transfers", response_model=list[TransferOut])
def list_transfers(
    organization_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[TransferOut]:
    return _svc(db).list_transfers(
        _actor(session), organization_id=organization_id, status=status_filter, limit=limit, offset=offset
    )


@router.post("/transfers", response_model=TransferDetailOut, status_code=201)
def create_transfer(
    payload: TransferCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> TransferDetailOut:
    out = _svc(db).create_transfer(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.transfer.create",
        target_type="logistics_warehouse_transfer",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"number={out.transfer_number};lines={len(out.lines)}",
    )
    return out


@router.post("/transfers/{transfer_id}/complete", response_model=TransferDetailOut)
def complete_transfer(
    transfer_id: str,
    payload: TransferCompleteRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> TransferDetailOut:
    return _svc(db).complete_transfer(transfer_id, payload, _actor(session))


@router.get("/rotable-cycles", response_model=list[RotableCycleOut])
def list_rotable_cycles(
    organization_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[RotableCycleOut]:
    return _svc(db).list_rotable_cycles(
        _actor(session), organization_id=organization_id, status=status_filter, limit=limit, offset=offset
    )


@router.post("/rotable-cycles", response_model=RotableCycleOut, status_code=201)
def open_rotable_cycle(
    payload: RotableCycleCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> RotableCycleOut:
    out = _svc(db).open_rotable_cycle(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.rotable_cycle.open",
        target_type="logistics_rotable_cycle",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"type={out.cycle_type}",
    )
    return out


@router.post("/rotable-cycles/{cycle_id}/close", response_model=RotableCycleOut)
def close_rotable_cycle(
    cycle_id: str,
    payload: RotableCycleCloseRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> RotableCycleOut:
    out = _svc(db).close_rotable_cycle(cycle_id, payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.rotable_cycle.close",
        target_type="logistics_rotable_cycle",
        target_id=out.id,
        organization_id=out.organization_id,
    )
    return out


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@router.get("/tools", response_model=list[ToolOut])
def list_tools(
    organization_id: str | None = None,
    q: str | None = None,
    status_filter: str | None = None,
    calibration_status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[ToolOut]:
    return _svc(db).list_tools(
        _actor(session),
        organization_id=organization_id,
        q=q,
        status=status_filter,
        calibration_status=calibration_status,
        limit=limit,
        offset=offset,
    )


@router.post("/tools", response_model=ToolOut, status_code=201)
def create_tool(
    payload: ToolCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_tools),
) -> ToolOut:
    out = _svc(db).create_tool(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.tool.create",
        target_type="logistics_tool",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"code={out.tool_code}",
    )
    return out


@router.get("/tools/{tool_id}", response_model=ToolOut)
def get_tool(
    tool_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> ToolOut:
    return _svc(db).get_tool(tool_id, _actor(session))


@router.put("/tools/{tool_id}", response_model=ToolOut)
def update_tool(
    tool_id: str,
    payload: ToolUpdate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_tools),
) -> ToolOut:
    out = _svc(db).update_tool(tool_id, payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.tool.update",
        target_type="logistics_tool",
        target_id=out.id,
        organization_id=out.organization_id,
    )
    return out


@router.get("/tools/{tool_id}/calibrations", response_model=list[ToolCalibrationOut])
def list_tool_calibrations(
    tool_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[ToolCalibrationOut]:
    return _svc(db).list_tool_calibrations(tool_id, _actor(session))


@router.post("/tools/{tool_id}/calibrate", response_model=ToolCalibrationOut, status_code=201)
def calibrate_tool(
    tool_id: str,
    payload: ToolCalibrateRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_tools),
) -> ToolCalibrationOut:
    return _svc(db).calibrate_tool(tool_id, payload, _actor(session))


@router.post("/tools/{tool_id}/reserve", response_model=ToolReservationOut, status_code=201)
def reserve_tool(
    tool_id: str,
    payload: ToolReserveRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_tools),
) -> ToolReservationOut:
    out = _svc(db).reserve_tool(tool_id, payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.tool.reserve",
        target_type="logistics_tool",
        target_id=tool_id,
        organization_id=out.organization_id,
    )
    return out


@router.post("/tools/{tool_id}/issue", response_model=ToolIssueOut, status_code=201)
def issue_tool(
    tool_id: str,
    payload: ToolIssueRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_tools),
) -> ToolIssueOut:
    return _svc(db).issue_tool(tool_id, payload, _actor(session))


@router.post("/tools/{tool_id}/return", response_model=ToolIssueOut)
def return_tool(
    tool_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_tools),
) -> ToolIssueOut:
    return _svc(db).return_tool(tool_id, _actor(session))


@router.post("/tools/{tool_id}/lost", response_model=LostToolReportOut, status_code=201)
def report_lost_tool(
    tool_id: str,
    payload: LostToolReportCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_tools),
) -> LostToolReportOut:
    return _svc(db).report_lost_tool(tool_id, payload, _actor(session))


@router.get("/tools/{tool_id}/history", response_model=list[ToolHistoryOut])
def list_tool_history(
    tool_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[ToolHistoryOut]:
    return _svc(db).list_tool_history(tool_id, _actor(session), limit=limit)


@router.get("/lost-tool-reports", response_model=list[LostToolReportOut])
def list_lost_tool_reports(
    organization_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[LostToolReportOut]:
    return _svc(db).list_lost_tool_reports(
        _actor(session), organization_id=organization_id, status=status_filter, limit=limit
    )


# ---------------------------------------------------------------------------
# Material requests
# ---------------------------------------------------------------------------


@router.get("/material-requests", response_model=list[MaterialRequestOut])
def list_material_requests(
    organization_id: str | None = None,
    status_filter: str | None = None,
    work_package_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[MaterialRequestOut]:
    return _svc(db).list_material_requests(
        _actor(session),
        organization_id=organization_id,
        status=status_filter,
        work_package_id=work_package_id,
        limit=limit,
        offset=offset,
    )


@router.post("/material-requests", response_model=MaterialRequestDetailOut, status_code=201)
def create_material_request(
    payload: MaterialRequestCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> MaterialRequestDetailOut:
    out = _svc(db).create_material_request(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.material_request.create",
        target_type="logistics_material_request",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"number={out.request_number};lines={len(out.lines)}",
    )
    return out


@router.get("/material-requests/{request_id}", response_model=MaterialRequestDetailOut)
def get_material_request(
    request_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> MaterialRequestDetailOut:
    return _svc(db).get_material_request(request_id, _actor(session))


@router.post("/material-requests/{request_id}/approve", response_model=MaterialRequestDetailOut)
def approve_material_request(
    request_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> MaterialRequestDetailOut:
    return _svc(db).approve_material_request(request_id, _actor(session))


@router.post("/material-requests/{request_id}/reserve", response_model=MaterialRequestDetailOut)
def reserve_material_request(
    request_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> MaterialRequestDetailOut:
    out = _svc(db).reserve_material_request(request_id, _actor(session))
    _audit(
        db,
        session,
        action="logistics.material_request.reserve",
        target_type="logistics_material_request",
        target_id=out.id,
        organization_id=out.organization_id,
    )
    return out


@router.post("/material-requests/{request_id}/issue", response_model=MaterialRequestDetailOut)
def issue_material_request(
    request_id: str,
    payload: MaterialRequestIssueRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> MaterialRequestDetailOut:
    return _svc(db).issue_material_request(request_id, payload, _actor(session))


@router.post("/material-requests/{request_id}/return", response_model=MaterialRequestDetailOut)
def return_material_request(
    request_id: str,
    payload: MaterialRequestReturnRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> MaterialRequestDetailOut:
    return _svc(db).return_material_request(request_id, payload, _actor(session))


@router.post("/material-requests/{request_id}/cancel", response_model=MaterialRequestDetailOut)
def cancel_material_request(
    request_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> MaterialRequestDetailOut:
    out = _svc(db).cancel_material_request(request_id, _actor(session))
    _audit(
        db,
        session,
        action="logistics.material_request.cancel",
        target_type="logistics_material_request",
        target_id=out.id,
        organization_id=out.organization_id,
    )
    return out


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------


@router.get("/vendors", response_model=list[VendorOut])
def list_vendors(
    organization_id: str | None = None,
    q: str | None = None,
    vendor_type: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[VendorOut]:
    return _svc(db).list_vendors(
        _actor(session),
        organization_id=organization_id,
        q=q,
        vendor_type=vendor_type,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post("/vendors", response_model=VendorOut, status_code=201)
def create_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_purchase),
) -> VendorOut:
    out = _svc(db).create_vendor(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.vendor.create",
        target_type="logistics_vendor",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"code={out.code}",
    )
    return out


@router.get("/vendors/{vendor_id}", response_model=VendorOut)
def get_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> VendorOut:
    return _svc(db).get_vendor(vendor_id, _actor(session))


@router.put("/vendors/{vendor_id}", response_model=VendorOut)
def update_vendor(
    vendor_id: str,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_purchase),
) -> VendorOut:
    out = _svc(db).update_vendor(vendor_id, payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.vendor.update",
        target_type="logistics_vendor",
        target_id=out.id,
        organization_id=out.organization_id,
    )
    return out


# ---------------------------------------------------------------------------
# Purchasing chain
# ---------------------------------------------------------------------------


@router.get("/purchase-requests", response_model=list[PurchaseRequestOut])
def list_purchase_requests(
    organization_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[PurchaseRequestOut]:
    return _svc(db).list_purchase_requests(
        _actor(session), organization_id=organization_id, status=status_filter, limit=limit, offset=offset
    )


@router.post("/purchase-requests", response_model=PurchaseRequestDetailOut, status_code=201)
def create_purchase_request(
    payload: PurchaseRequestCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_purchase),
) -> PurchaseRequestDetailOut:
    out = _svc(db).create_purchase_request(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.purchase_request.create",
        target_type="logistics_purchase_request",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"number={out.request_number};lines={len(out.lines)}",
    )
    return out


@router.get("/purchase-requests/{request_id}", response_model=PurchaseRequestDetailOut)
def get_purchase_request(
    request_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> PurchaseRequestDetailOut:
    return _svc(db).get_purchase_request(request_id, _actor(session))


@router.post("/purchase-requests/{request_id}/approve", response_model=PurchaseRequestDetailOut)
def approve_purchase_request(
    request_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_purchase),
) -> PurchaseRequestDetailOut:
    return _svc(db).approve_purchase_request(request_id, _actor(session))


@router.post("/purchase-requests/{request_id}/rfq", response_model=RfqDetailOut, status_code=201)
def create_rfq(
    request_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_purchase),
) -> RfqDetailOut:
    out = _svc(db).create_rfq(request_id, _actor(session))
    _audit(
        db,
        session,
        action="logistics.rfq.create",
        target_type="logistics_rfq",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"number={out.rfq_number}",
    )
    return out


@router.get("/rfqs", response_model=list[RfqOut])
def list_rfqs(
    organization_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[RfqOut]:
    return _svc(db).list_rfqs(
        _actor(session), organization_id=organization_id, status=status_filter, limit=limit, offset=offset
    )


@router.get("/rfqs/{rfq_id}", response_model=RfqDetailOut)
def get_rfq(
    rfq_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> RfqDetailOut:
    return _svc(db).get_rfq(rfq_id, _actor(session))


@router.post("/rfqs/{rfq_id}/quotes", response_model=RfqQuoteOut, status_code=201)
def add_quote(
    rfq_id: str,
    payload: RfqQuoteCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_purchase),
) -> RfqQuoteOut:
    out = _svc(db).add_quote(rfq_id, payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.rfq.quote.create",
        target_type="logistics_rfq_quote",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"vendor={out.vendor_id};price={out.unit_price}",
    )
    return out


@router.post("/rfqs/{rfq_id}/quotes/{quote_id}/select", response_model=RfqDetailOut)
def select_quote(
    rfq_id: str,
    quote_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_purchase),
) -> RfqDetailOut:
    return _svc(db).select_quote(rfq_id, quote_id, _actor(session))


@router.post("/rfqs/{rfq_id}/purchase-order", response_model=PurchaseOrderDetailOut, status_code=201)
def create_purchase_order(
    rfq_id: str,
    payload: PurchaseOrderCreateFromRfq,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_purchase),
) -> PurchaseOrderDetailOut:
    return _svc(db).create_purchase_order_from_rfq(rfq_id, payload, _actor(session))


@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    organization_id: str | None = None,
    status_filter: str | None = None,
    vendor_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[PurchaseOrderOut]:
    return _svc(db).list_purchase_orders(
        _actor(session),
        organization_id=organization_id,
        status=status_filter,
        vendor_id=vendor_id,
        limit=limit,
        offset=offset,
    )


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderDetailOut)
def get_purchase_order(
    po_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> PurchaseOrderDetailOut:
    return _svc(db).get_purchase_order(po_id, _actor(session))


@router.post("/purchase-orders/{po_id}/receive", response_model=ReceiptDetailOut, status_code=201)
def receive_purchase_order(
    po_id: str,
    payload: ReceiptCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> ReceiptDetailOut:
    return _svc(db).receive_purchase_order(po_id, payload, _actor(session))


@router.post("/purchase-orders/{po_id}/invoices", response_model=VendorInvoiceOut, status_code=201)
def create_vendor_invoice(
    po_id: str,
    payload: VendorInvoiceCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_purchase),
) -> VendorInvoiceOut:
    return _svc(db).create_vendor_invoice(po_id, payload, _actor(session))


@router.get("/purchase-orders/{po_id}/invoices", response_model=list[VendorInvoiceOut])
def list_vendor_invoices(
    po_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[VendorInvoiceOut]:
    return _svc(db).list_vendor_invoices(_actor(session), purchase_order_id=po_id)


@router.post("/purchase-orders/{po_id}/close", response_model=PurchaseOrderDetailOut)
def close_purchase_order(
    po_id: str,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_purchase),
) -> PurchaseOrderDetailOut:
    return _svc(db).close_purchase_order(po_id, _actor(session))


@router.get("/receipts", response_model=list[ReceiptOut])
def list_receipts(
    organization_id: str | None = None,
    status_filter: str | None = None,
    purchase_order_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[ReceiptOut]:
    return _svc(db).list_receipts(
        _actor(session),
        organization_id=organization_id,
        status=status_filter,
        purchase_order_id=purchase_order_id,
        limit=limit,
        offset=offset,
    )


@router.post("/receipts/{receipt_id}/inspect", response_model=ReceiptDetailOut)
def inspect_receipt(
    receipt_id: str,
    payload: ReceiptInspectRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> ReceiptDetailOut:
    return _svc(db).inspect_receipt(receipt_id, payload, _actor(session))


@router.post("/receipts/{receipt_id}/putaway", response_model=ReceiptDetailOut)
def putaway_receipt(
    receipt_id: str,
    payload: ReceiptPutawayRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> ReceiptDetailOut:
    return _svc(db).putaway_receipt(receipt_id, payload, _actor(session))


# ---------------------------------------------------------------------------
# Shipments, scanning, dashboard, seed
# ---------------------------------------------------------------------------


@router.get("/shipments", response_model=list[ShipmentOut])
def list_shipments(
    organization_id: str | None = None,
    direction: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> list[ShipmentOut]:
    return _svc(db).list_shipments(
        _actor(session),
        organization_id=organization_id,
        direction=direction,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post("/shipments", response_model=ShipmentOut, status_code=201)
def create_shipment(
    payload: ShipmentCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_stores),
) -> ShipmentOut:
    out = _svc(db).create_shipment(payload, _actor(session))
    _audit(
        db,
        session,
        action="logistics.shipment.create",
        target_type="logistics_shipment",
        target_id=out.id,
        organization_id=out.organization_id,
        details=f"number={out.shipment_number};direction={out.direction}",
    )
    return out


@router.post("/scan", response_model=ScanOut)
def scan(
    payload: ScanRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> ScanOut:
    return _svc(db).scan(payload, _actor(session))


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> DashboardOut:
    return _svc(db).dashboard(_actor(session), organization_id=organization_id)


@router.get("/shortages", response_model=ShortagesOut)
def shortages(
    organization_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_read),
) -> ShortagesOut:
    return _svc(db).list_shortages(_actor(session), organization_id=organization_id, limit=limit)


@router.post("/material-planning/run", response_model=MaterialPlanningResult)
def run_material_planning(
    payload: MaterialPlanningRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> MaterialPlanningResult:
    actor = _actor(session)
    svc = _svc(db)
    org_id = svc.resolve_org_id(actor, None)
    out = svc.run_material_planning(
        org_id,
        payload.work_package_id,
        payload.lines,
        username=actor.username,
        actor=actor,
        auto_purchase_request=payload.auto_purchase_request,
    )
    _audit(
        db,
        session,
        action="logistics.planning.material",
        target_type="work_package",
        target_id=payload.work_package_id or org_id,
        details=f"reserved={out.reserved_lines};shortage={out.shortage_lines}",
    )
    return out


@router.post("/tool-planning/run", response_model=ToolPlanningResult)
def run_tool_planning(
    payload: ToolPlanningRequest,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_tools),
) -> ToolPlanningResult:
    actor = _actor(session)
    svc = _svc(db)
    org_id = svc.resolve_org_id(actor, None)
    out = svc.run_tool_planning(
        org_id,
        payload.work_package_id,
        payload.lines,
        username=actor.username,
        actor=actor,
    )
    _audit(
        db,
        session,
        action="logistics.planning.tools",
        target_type="work_package",
        target_id=payload.work_package_id or org_id,
        details=f"reserved={out.reserved_lines};unavailable={out.unavailable_lines}",
    )
    return out


@router.post("/seed-demo", response_model=SeedDemoOut, status_code=201)
def seed_demo(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> SeedDemoOut:
    actor = _actor(session)
    svc = _svc(db)
    org_id = svc.resolve_org_id(actor, organization_id)
    out = svc.seed_demo(org_id, actor=actor)
    if out.created:
        _audit(
            db,
            session,
            action="logistics.seed_demo",
            target_type="organization",
            target_id=org_id,
            organization_id=org_id,
            details=f"warehouse={out.warehouse_id};parts={len(out.part_ids)}",
        )
    return out
