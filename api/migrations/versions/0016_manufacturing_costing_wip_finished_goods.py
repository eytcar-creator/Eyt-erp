"""E.Y.T ERP manufacturing costing, WIP and finished goods cost

Revision ID: 0016
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cost_centers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(60), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(200), nullable=False),
        sa.Column("cost_center_type", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("cost_center_type IN ('PRODUCTION','LABOR','MACHINE','OVERHEAD','OUTSOURCING','QC','WAREHOUSE')", name="ck_cost_center_type"),
    )
    op.create_table(
        "production_cost_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_order_id", UUID(as_uuid=True), sa.ForeignKey("work_orders.id", ondelete="SET NULL")),
        sa.Column("outsourcing_order_id", UUID(as_uuid=True), sa.ForeignKey("outsourcing_orders.id", ondelete="SET NULL")),
        sa.Column("cost_center_id", UUID(as_uuid=True), sa.ForeignKey("cost_centers.id", ondelete="RESTRICT")),
        sa.Column("cost_type", sa.String(30), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT")),
        sa.Column("quantity", sa.Numeric(18, 6)),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reference_type", sa.String(50)),
        sa.Column("reference_id", UUID(as_uuid=True)),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("cost_type IN ('MATERIAL','LABOR','MACHINE','OUTSOURCING','OVERHEAD','SCRAP','ADJUSTMENT')", name="ck_production_cost_type"),
        sa.CheckConstraint("unit_cost >= 0 AND total_cost >= 0", name="ck_production_cost_nonnegative"),
    )
    op.create_table(
        "wip_cost_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("material_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("labor_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("machine_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("outsourcing_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("overhead_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("scrap_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(18, 4), nullable=False),
        sa.CheckConstraint("material_cost >= 0 AND labor_cost >= 0 AND machine_cost >= 0 AND outsourcing_cost >= 0 AND overhead_cost >= 0 AND scrap_cost >= 0 AND total_cost >= 0", name="ck_wip_cost_nonnegative"),
    )
    op.create_table(
        "finished_goods_costs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_produced", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_production_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("cost_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("quantity_produced > 0", name="ck_finished_goods_quantity_positive"),
        sa.CheckConstraint("total_production_cost >= 0 AND unit_cost >= 0", name="ck_finished_goods_cost_nonnegative"),
        sa.CheckConstraint("cost_status IN ('DRAFT','CALCULATED','POSTED','ADJUSTED')", name="ck_finished_goods_cost_status"),
        sa.UniqueConstraint("production_order_id", name="uq_finished_goods_cost_production_order"),
    )
    op.create_index("idx_cost_entries_production_type", "production_cost_entries", ["production_order_id", "cost_type"])
    op.create_index("idx_cost_entries_center_date", "production_cost_entries", ["cost_center_id", "occurred_at"])
    op.create_index("idx_wip_snapshot_production_date", "wip_cost_snapshots", ["production_order_id", "snapshot_at"])
    op.create_index("idx_finished_goods_product_date", "finished_goods_costs", ["product_id", "calculated_at"])


def downgrade():
    op.drop_index("idx_finished_goods_product_date", table_name="finished_goods_costs")
    op.drop_index("idx_wip_snapshot_production_date", table_name="wip_cost_snapshots")
    op.drop_index("idx_cost_entries_center_date", table_name="production_cost_entries")
    op.drop_index("idx_cost_entries_production_type", table_name="production_cost_entries")
    op.drop_table("finished_goods_costs")
    op.drop_table("wip_cost_snapshots")
    op.drop_table("production_cost_entries")
    op.drop_table("cost_centers")
