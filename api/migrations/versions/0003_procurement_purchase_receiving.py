"""E.Y.T ERP procurement, purchase orders and receiving

Revision ID: 0003
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "purchase_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("po_no", sa.String(80), nullable=False, unique=True),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT")),
        sa.Column("order_date", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("expected_date", sa.Date()),
        sa.Column("status", sa.String(25), nullable=False, server_default="DRAFT"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="IRR"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("status IN ('DRAFT','APPROVED','SENT','PARTIAL','RECEIVED','CANCELLED')", name="ck_po_status"),
    )
    op.create_table(
        "purchase_order_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("purchase_order_id", UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ordered_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("received_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.CheckConstraint("ordered_qty > 0", name="ck_po_item_ordered_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_po_item_price_nonnegative"),
        sa.CheckConstraint("received_qty >= 0 AND received_qty <= ordered_qty", name="ck_po_item_received_valid"),
    )
    op.create_table(
        "receipts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("receipt_no", sa.String(80), nullable=False, unique=True),
        sa.Column("purchase_order_id", UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id", ondelete="RESTRICT")),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(20), nullable=False, server_default="RECEIVED"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("status IN ('RECEIVED','QC_HOLD','ACCEPTED','REJECTED','CANCELLED')", name="ck_receipt_status"),
    )
    op.create_table(
        "receipt_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("receipt_id", UUID(as_uuid=True), sa.ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.CheckConstraint("quantity > 0", name="ck_receipt_item_positive"),
        sa.CheckConstraint("accepted_qty >= 0 AND rejected_qty >= 0 AND accepted_qty + rejected_qty <= quantity", name="ck_receipt_item_disposition"),
    )
    op.create_index("idx_po_supplier_date", "purchase_orders", ["supplier_id", "order_date"])
    op.create_index("idx_po_status_expected", "purchase_orders", ["status", "expected_date"])
    op.create_index("idx_receipts_po", "receipts", ["purchase_order_id"])
    op.create_index("idx_receipts_date", "receipts", ["received_at"])


def downgrade():
    op.drop_index("idx_receipts_date", table_name="receipts")
    op.drop_index("idx_receipts_po", table_name="receipts")
    op.drop_index("idx_po_status_expected", table_name="purchase_orders")
    op.drop_index("idx_po_supplier_date", table_name="purchase_orders")
    op.drop_table("receipt_items")
    op.drop_table("receipts")
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
