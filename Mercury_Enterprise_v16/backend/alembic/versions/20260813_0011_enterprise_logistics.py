"""Program B: enterprise logistics — warehouses, stock, tools, purchasing."""

from __future__ import annotations

from alembic import op

revision = "20260813_0011"
down_revision = "20260813_0010"
branch_labels = None
depends_on = None

LOGISTICS_TABLES = {
    "logistics_warehouses",
    "logistics_buildings",
    "logistics_stores",
    "logistics_rooms",
    "logistics_zones",
    "logistics_aisles",
    "logistics_shelves",
    "logistics_bins",
    "logistics_locations",
    "logistics_warehouse_transfers",
    "logistics_warehouse_transfer_lines",
    "logistics_part_masters",
    "logistics_part_families",
    "logistics_part_family_members",
    "logistics_part_supersessions",
    "logistics_part_attachments",
    "logistics_part_identifiers",
    "logistics_stock_balances",
    "logistics_stock_units",
    "logistics_stock_movements",
    "logistics_reservations",
    "logistics_tools",
    "logistics_tool_kits",
    "logistics_tool_kit_members",
    "logistics_shadow_boards",
    "logistics_tool_calibrations",
    "logistics_tool_issues",
    "logistics_tool_reservations",
    "logistics_lost_tool_reports",
    "logistics_tool_history",
    "logistics_material_requests",
    "logistics_material_request_lines",
    "logistics_vendors",
    "logistics_rotable_cycles",
    "logistics_purchase_requests",
    "logistics_purchase_request_lines",
    "logistics_rfqs",
    "logistics_rfq_quotes",
    "logistics_purchase_orders",
    "logistics_purchase_order_lines",
    "logistics_shipments",
    "logistics_receipts",
    "logistics_receipt_lines",
    "logistics_vendor_invoices",
}


def upgrade() -> None:
    from app.database import Base
    from app.logistics import models as logistics_models  # noqa: F401

    bind = op.get_bind()
    tables = [t for t in Base.metadata.sorted_tables if t.name in LOGISTICS_TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    # Reverse dependency order: children before the rows they reference.
    for name in (
        "logistics_vendor_invoices",
        "logistics_receipt_lines",
        "logistics_receipts",
        "logistics_shipments",
        "logistics_purchase_order_lines",
        "logistics_purchase_orders",
        "logistics_rfq_quotes",
        "logistics_rfqs",
        "logistics_purchase_request_lines",
        "logistics_purchase_requests",
        "logistics_rotable_cycles",
        "logistics_vendors",
        "logistics_material_request_lines",
        "logistics_material_requests",
        "logistics_tool_history",
        "logistics_lost_tool_reports",
        "logistics_tool_reservations",
        "logistics_tool_issues",
        "logistics_tool_calibrations",
        "logistics_shadow_boards",
        "logistics_tool_kit_members",
        "logistics_tool_kits",
        "logistics_part_identifiers",
        "logistics_tools",
        "logistics_warehouse_transfer_lines",
        "logistics_warehouse_transfers",
        "logistics_reservations",
        "logistics_stock_movements",
        "logistics_stock_units",
        "logistics_stock_balances",
        "logistics_part_attachments",
        "logistics_part_supersessions",
        "logistics_part_family_members",
        "logistics_part_families",
        "logistics_part_masters",
        "logistics_locations",
        "logistics_bins",
        "logistics_shelves",
        "logistics_aisles",
        "logistics_zones",
        "logistics_rooms",
        "logistics_stores",
        "logistics_buildings",
        "logistics_warehouses",
    ):
        op.drop_table(name)
