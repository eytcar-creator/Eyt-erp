"""E.Y.T ERP demand planning, reorder points, MRP and shortage alerts

Revision ID: 0017
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reorder_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reorder_point", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("target_stock", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("safety_stock", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("lead_time_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("reorder_point >= 0 AND target_stock >= 0 AND safety_stock >= 0", name="ck_reorder_stock_nonnegative"),
        sa.CheckConstraint("lead_time_days >= 0", name="ck_reorder_lead_time_nonnegative"),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_reorder_policy_product_warehouse"),
    )
    op.create_table(
        "demand_forecasts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="SET NULL")),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("forecast_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("forecast_source", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("confidence", sa.Numeric(5, 2)),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("forecast_quantity >= 0", name="ck_forecast_quantity_nonnegative"),
        sa.CheckConstraint("forecast_source IN ('MANUAL','SALES_HISTORY','CUSTOMER_ORDER','SEASONAL','MIXED')", name="ck_forecast_source"),
        sa.CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 100", name="ck_forecast_confidence"),
    )
    op.create_table(
        "mrp_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_no", sa.String(80), nullable=False, unique=True),
        sa.Column("run_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("planning_horizon_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("planning_horizon_days > 0", name="ck_mrp_horizon_positive"),
        sa.CheckConstraint("status IN ('DRAFT','RUNNING','COMPLETED','FAILED','CANCELLED')", name="ck_mrp_run_status"),
    )
    op.create_table(
        "mrp_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mrp_run_id", UUID(as_uuid=True), sa.ForeignKey("mrp_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="SET NULL")),
        sa.Column("recommendation_type", sa.String(20), nullable=False),
        sa.Column("required_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("available_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("net_requirement", sa.Numeric(18, 6), nullable=False),
        sa.Column("recommended_date", sa.Date()),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("source_reference", sa.String(100)),
        sa.CheckConstraint("recommendation_type IN ('PURCHASE','PRODUCE','TRANSFER')", name="ck_mrp_recommendation_type"),
        sa.CheckConstraint("required_quantity >= 0 AND available_quantity >= 0 AND net_requirement >= 0", name="ck_mrp_quantities_nonnegative"),
        sa.CheckConstraint("status IN ('OPEN','APPROVED','CONVERTED','IGNORED','CANCELLED')", name="ck_mrp_recommendation_status"),
    )
    op.create_table(
        "material_shortage_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="SET NULL")),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="SET NULL")),
        sa.Column("mrp_run_id", UUID(as_uuid=True), sa.ForeignKey("mrp_runs.id", ondelete="SET NULL")),
        sa.Column("required_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("available_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("shortage_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("required_quantity >= 0 AND available_quantity >= 0 AND shortage_quantity > 0", name="ck_shortage_quantities"),
        sa.CheckConstraint("severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="ck_shortage_severity"),
        sa.CheckConstraint("status IN ('OPEN','ACKNOWLEDGED','RESOLVED','IGNORED')", name="ck_shortage_status"),
    )
    op.create_index("idx_reorder_product_warehouse", "reorder_policies", ["product_id", "warehouse_id"])
    op.create_index("idx_forecast_product_date", "demand_forecasts", ["product_id", "forecast_date"])
    op.create_index("idx_mrp_recommendation_run_status", "mrp_recommendations", ["mrp_run_id", "status"])
    op.create_index("idx_shortage_status_severity", "material_shortage_alerts", ["status", "severity", "detected_at"])


def downgrade():
    op.drop_index("idx_shortage_status_severity", table_name="material_shortage_alerts")
    op.drop_index("idx_mrp_recommendation_run_status", table_name="mrp_recommendations")
    op.drop_index("idx_forecast_product_date", table_name="demand_forecasts")
    op.drop_index("idx_reorder_product_warehouse", table_name="reorder_policies")
    op.drop_table("material_shortage_alerts")
    op.drop_table("mrp_recommendations")
    op.drop_table("mrp_runs")
    op.drop_table("demand_forecasts")
    op.drop_table("reorder_policies")
