"""E.Y.T ERP multi-warehouse stock transfers and warehouse operations

Revision ID: 0013
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "warehouse_locations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name_fa", sa.String(160), nullable=False),
        sa.Column("location_type", sa.String(30), nullable=False, server_default="STORAGE"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("warehouse_id", "code", name="uq_warehouse_location_code"),
        sa.CheckConstraint("location_type IN ('RECEIVING','STORAGE','PICKING','QUARANTINE','SHIPPING','PRODUCTION','RETURN')", name="ck_location_type"),
    )
    op.create_table(
        "stock_transfers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("transfer_no", sa.String(80), nullable=False, unique=True),
        sa.Column("source_warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destination_warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(25), nullable=False, server_default="DRAFT"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("shipped_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("source_warehouse_id <> destination_warehouse_id", name="ck_transfer_different_warehouses"),
        sa.CheckConstraint("status IN ('DRAFT','REQUESTED','APPROVED','PICKED','IN_TRANSIT','RECEIVED','CANCELLED')", name="ck_transfer_status"),
    )
    op.create_table(
        "stock_transfer_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("transfer_id", UUID(as_uuid=True), sa.ForeignKey("stock_transfers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_requested", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_shipped", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("quantity_received", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.CheckConstraint("quantity_requested > 0", name="ck_transfer_requested_positive"),
        sa.CheckConstraint("quantity_shipped >= 0 AND quantity_shipped <= quantity_requested", name="ck_transfer_shipped_range"),
        sa.CheckConstraint("quantity_received >= 0 AND quantity_received <= quantity_shipped", name="ck_transfer_received_range"),
    )
    op.create_table(
        "stock_operation_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("location_id", UUID(as_uuid=True), sa.ForeignKey("warehouse_locations.id", ondelete="RESTRICT")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_type", sa.String(30), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("reference_type", sa.String(50)),
        sa.Column("reference_id", UUID(as_uuid=True)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("quantity > 0", name="ck_stock_operation_positive"),
        sa.CheckConstraint("operation_type IN ('RECEIPT','ISSUE','TRANSFER_OUT','TRANSFER_IN','ADJUSTMENT','QUARANTINE','RELEASE','RETURN')", name="ck_stock_operation_type"),
    )
    op.create_index("idx_warehouse_locations_warehouse", "warehouse_locations", ["warehouse_id"])
    op.create_index("idx_stock_transfers_route_status", "stock_transfers", ["source_warehouse_id", "destination_warehouse_id", "status"])
    op.create_index("idx_transfer_items_product", "stock_transfer_items", ["product_id"])
    op.create_index("idx_stock_ops_warehouse_product", "stock_operation_lines", ["warehouse_id", "product_id", "occurred_at"])


def downgrade():
    op.drop_index("idx_stock_ops_warehouse_product", table_name="stock_operation_lines")
    op.drop_index("idx_transfer_items_product", table_name="stock_transfer_items")
    op.drop_index("idx_stock_transfers_route_status", table_name="stock_transfers")
    op.drop_index("idx_warehouse_locations_warehouse", table_name="warehouse_locations")
    op.drop_table("stock_operation_lines")
    op.drop_table("stock_transfer_items")
    op.drop_table("stock_transfers")
    op.drop_table("warehouse_locations")
