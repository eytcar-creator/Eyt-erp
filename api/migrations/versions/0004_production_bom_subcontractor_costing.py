"""E.Y.T ERP production, BOM, subcontracting and costing

Revision ID: 0004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0004"
down_revision = "0003"
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
        sa.UniqueConstraint("product_id", "version", name="uq_bom_product_version"),
        sa.CheckConstraint("quantity_output > 0", name="ck_bom_output_positive"),
    )
    op.create_table(
        "bom_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bom_id", UUID(as_uuid=True), sa.ForeignKey("boms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("scrap_percent", sa.Numeric(7, 3), nullable=False, server_default="0"),
        sa.CheckConstraint("quantity > 0", name="ck_bom_item_positive"),
        sa.CheckConstraint("scrap_percent BETWEEN 0 AND 100", name="ck_bom_scrap_valid"),
    )
    op.create_table(
        "production_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("production_no", sa.String(80), nullable=False, unique=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bom_id", UUID(as_uuid=True), sa.ForeignKey("boms.id", ondelete="RESTRICT")),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT")),
        sa.Column("planned_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("completed_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("status", sa.String(25), nullable=False, server_default="PLANNED"),
        sa.Column("planned_start", sa.DateTime(timezone=True)),
        sa.Column("planned_end", sa.DateTime(timezone=True)),
        sa.Column("actual_start", sa.DateTime(timezone=True)),
        sa.Column("actual_end", sa.DateTime(timezone=True)),
        sa.CheckConstraint("planned_qty > 0", name="ck_prod_planned_positive"),
        sa.CheckConstraint("completed_qty >= 0 AND completed_qty <= planned_qty", name="ck_prod_completed_valid"),
        sa.CheckConstraint("status IN ('PLANNED','RELEASED','IN_PROGRESS','HOLD','COMPLETED','CANCELLED')", name="ck_prod_status"),
    )
    op.create_table(
        "subcontractor_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subcontract_no", sa.String(80), nullable=False, unique=True),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="RESTRICT")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expected_return_at", sa.DateTime(timezone=True)),
        sa.Column("actual_return_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(25), nullable=False, server_default="SENT"),
        sa.CheckConstraint("status IN ('SENT','PARTIAL','RETURNED','OVERDUE','CANCELLED')", name="ck_subcontract_status"),
    )
    op.create_table(
        "production_costs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cost_type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("incurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("amount >= 0", name="ck_prod_cost_nonnegative"),
        sa.CheckConstraint("cost_type IN ('MATERIAL','LABOR','MACHINE','SUBCONTRACT','OVERHEAD','SCRAP','REWORK','SLEEP_TIME','OTHER')", name="ck_prod_cost_type"),
    )
    op.create_index("idx_prod_orders_status", "production_orders", ["status"])
    op.create_index("idx_prod_orders_product", "production_orders", ["product_id"])
    op.create_index("idx_subcontract_expected", "subcontractor_orders", ["status", "expected_return_at"])
    op.create_index("idx_prod_costs_order", "production_costs", ["production_order_id"])


def downgrade():
    op.drop_index("idx_prod_costs_order", table_name="production_costs")
    op.drop_index("idx_subcontract_expected", table_name="subcontractor_orders")
    op.drop_index("idx_prod_orders_product", table_name="production_orders")
    op.drop_index("idx_prod_orders_status", table_name="production_orders")
    op.drop_table("production_costs")
    op.drop_table("subcontractor_orders")
    op.drop_table("production_orders")
    op.drop_table("bom_items")
    op.drop_table("boms")
