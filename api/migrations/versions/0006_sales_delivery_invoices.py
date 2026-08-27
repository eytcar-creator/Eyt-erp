"""E.Y.T ERP sales, delivery and invoices

Revision ID: 0006
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sales_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_no", sa.String(80), nullable=False, unique=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT")),
        sa.Column("order_date", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("status", sa.String(25), nullable=False, server_default="DRAFT"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="IRR"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("status IN ('DRAFT','CONFIRMED','RESERVED','PARTIAL','DELIVERED','CANCELLED')", name="ck_sales_order_status"),
    )
    op.create_table(
        "sales_order_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sales_order_id", UUID(as_uuid=True), sa.ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.CheckConstraint("quantity > 0", name="ck_sales_item_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_sales_item_price_nonnegative"),
        sa.CheckConstraint("discount_amount >= 0", name="ck_sales_item_discount_nonnegative"),
    )
    op.create_table(
        "deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("delivery_no", sa.String(80), nullable=False, unique=True),
        sa.Column("sales_order_id", UUID(as_uuid=True), sa.ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(25), nullable=False, server_default="PENDING"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("status IN ('PENDING','PICKED','SHIPPED','DELIVERED','CANCELLED')", name="ck_delivery_status"),
    )
    op.create_table(
        "delivery_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("delivery_id", UUID(as_uuid=True), sa.ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_delivery_item_positive"),
    )
    op.create_table(
        "sales_invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("invoice_no", sa.String(80), nullable=False, unique=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sales_order_id", UUID(as_uuid=True), sa.ForeignKey("sales_orders.id", ondelete="RESTRICT")),
        sa.Column("invoice_date", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("due_date", sa.Date()),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("discount_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("tax_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("grand_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ISSUED"),
        sa.CheckConstraint("subtotal >= 0 AND discount_total >= 0 AND tax_total >= 0 AND grand_total >= 0", name="ck_invoice_amounts_nonnegative"),
        sa.CheckConstraint("status IN ('DRAFT','ISSUED','PARTIAL_PAID','PAID','VOID','OVERDUE')", name="ck_invoice_status"),
    )
    op.create_table(
        "sales_invoice_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("sales_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.CheckConstraint("quantity > 0", name="ck_invoice_item_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0 AND discount_amount >= 0 AND tax_amount >= 0", name="ck_invoice_item_amounts_nonnegative"),
    )
    op.create_index("idx_sales_orders_customer_date", "sales_orders", ["customer_id", "order_date"])
    op.create_index("idx_sales_orders_status", "sales_orders", ["status"])
    op.create_index("idx_deliveries_status", "deliveries", ["status"])
    op.create_index("idx_invoices_customer_due", "sales_invoices", ["customer_id", "due_date"])
    op.create_index("idx_invoices_status", "sales_invoices", ["status"])


def downgrade():
    op.drop_index("idx_invoices_status", table_name="sales_invoices")
    op.drop_index("idx_invoices_customer_due", table_name="sales_invoices")
    op.drop_index("idx_deliveries_status", table_name="deliveries")
    op.drop_index("idx_sales_orders_status", table_name="sales_orders")
    op.drop_index("idx_sales_orders_customer_date", table_name="sales_orders")
    op.drop_table("sales_invoice_items")
    op.drop_table("sales_invoices")
    op.drop_table("delivery_items")
    op.drop_table("deliveries")
    op.drop_table("sales_order_items")
    op.drop_table("sales_orders")
