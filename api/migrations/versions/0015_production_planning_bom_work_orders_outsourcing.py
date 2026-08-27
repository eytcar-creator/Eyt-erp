"""E.Y.T ERP production planning, BOM, work orders and outsourcing

Revision ID: 0015
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "boms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.String(30), nullable=False),
        sa.Column("quantity_output", sa.Numeric(18, 6), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("quantity_output > 0", name="ck_bom_output_positive"),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="ck_bom_dates"),
        sa.UniqueConstraint("product_id", "version", name="uq_bom_product_version"),
    )
    op.create_table(
        "bom_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bom_id", UUID(as_uuid=True), sa.ForeignKey("boms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("scrap_percent", sa.Numeric(7, 3), nullable=False, server_default="0"),
        sa.Column("operation_note", sa.Text()),
        sa.CheckConstraint("quantity > 0", name="ck_bom_item_quantity_positive"),
        sa.CheckConstraint("scrap_percent BETWEEN 0 AND 100", name="ck_bom_scrap_percent"),
    )
    op.create_table(
        "production_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("production_no", sa.String(80), nullable=False, unique=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bom_id", UUID(as_uuid=True), sa.ForeignKey("boms.id", ondelete="RESTRICT")),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT")),
        sa.Column("planned_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("completed_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("planned_start", sa.DateTime(timezone=True)),
        sa.Column("planned_end", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(25), nullable=False, server_default="DRAFT"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("planned_quantity > 0", name="ck_production_planned_positive"),
        sa.CheckConstraint("completed_quantity >= 0 AND completed_quantity <= planned_quantity", name="ck_production_completed_range"),
        sa.CheckConstraint("planned_end IS NULL OR planned_start IS NULL OR planned_end >= planned_start", name="ck_production_dates"),
        sa.CheckConstraint("status IN ('DRAFT','PLANNED','RELEASED','IN_PROGRESS','PAUSED','COMPLETED','CANCELLED')", name="ck_production_status"),
    )
    op.create_table(
        "work_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("work_order_no", sa.String(80), nullable=False, unique=True),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operation_name", sa.String(150), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("work_center", sa.String(120)),
        sa.Column("planned_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("completed_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("status", sa.String(25), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("sequence_no > 0", name="ck_work_order_sequence_positive"),
        sa.CheckConstraint("planned_qty > 0 AND completed_qty >= 0 AND completed_qty <= planned_qty", name="ck_work_order_qty_range"),
        sa.CheckConstraint("status IN ('PENDING','READY','IN_PROGRESS','DONE','BLOCKED','CANCELLED')", name="ck_work_order_status"),
        sa.UniqueConstraint("production_order_id", "sequence_no", name="uq_work_order_sequence"),
    )
    op.create_table(
        "outsourcing_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("outsourcing_no", sa.String(80), nullable=False, unique=True),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_name", sa.String(150), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(25), nullable=False, server_default="DRAFT"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("quantity > 0", name="ck_outsource_quantity_positive"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_outsource_cost_nonnegative"),
        sa.CheckConstraint("status IN ('DRAFT','SENT','IN_PROCESS','RECEIVED','QC_HOLD','COMPLETED','CANCELLED')", name="ck_outsource_status"),
    )
    op.create_index("idx_bom_product_active", "boms", ["product_id", "is_active"])
    op.create_index("idx_bom_items_component", "bom_items", ["component_product_id"])
    op.create_index("idx_production_product_status", "production_orders", ["product_id", "status"])
    op.create_index("idx_work_orders_production_status", "work_orders", ["production_order_id", "status"])
    op.create_index("idx_outsourcing_supplier_status", "outsourcing_orders", ["supplier_id", "status"])


def downgrade():
    op.drop_index("idx_outsourcing_supplier_status", table_name="outsourcing_orders")
    op.drop_index("idx_work_orders_production_status", table_name="work_orders")
    op.drop_index("idx_production_product_status", table_name="production_orders")
    op.drop_index("idx_bom_items_component", table_name="bom_items")
    op.drop_index("idx_bom_product_active", table_name="boms")
    op.drop_table("outsourcing_orders")
    op.drop_table("work_orders")
    op.drop_table("production_orders")
    op.drop_table("bom_items")
    op.drop_table("boms")
