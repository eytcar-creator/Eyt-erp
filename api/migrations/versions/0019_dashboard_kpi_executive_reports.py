"""E.Y.T ERP dashboard, KPI and executive reports

Revision ID: 0019
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "kpi_definitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(200), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("unit", sa.String(30)),
        sa.Column("target_value", sa.Numeric(20, 6)),
        sa.Column("warning_threshold", sa.Numeric(20, 6)),
        sa.Column("critical_threshold", sa.Numeric(20, 6)),
        sa.Column("calculation_key", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("category IN ('SALES','FINANCE','INVENTORY','PRODUCTION','QUALITY','CUSTOMER','SUPPLIER','CASHFLOW')", name="ck_kpi_category"),
    )
    op.create_table(
        "kpi_values",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kpi_id", UUID(as_uuid=True), sa.ForeignKey("kpi_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(20, 6), nullable=False),
        sa.Column("target_value", sa.Numeric(20, 6)),
        sa.Column("status", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("period_end >= period_start", name="ck_kpi_value_period"),
        sa.CheckConstraint("status IN ('NORMAL','WARNING','CRITICAL','NO_DATA')", name="ck_kpi_value_status"),
        sa.UniqueConstraint("kpi_id", "period_start", "period_end", name="uq_kpi_value_period"),
    )
    op.create_table(
        "dashboards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(200), nullable=False),
        sa.Column("dashboard_type", sa.String(30), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("dashboard_type IN ('EXECUTIVE','SALES','FINANCE','INVENTORY','PRODUCTION','QUALITY','CUSTOM')", name="ck_dashboard_type"),
    )
    op.create_table(
        "dashboard_widgets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("dashboard_id", UUID(as_uuid=True), sa.ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kpi_id", UUID(as_uuid=True), sa.ForeignKey("kpi_definitions.id", ondelete="SET NULL")),
        sa.Column("title_fa", sa.String(200), nullable=False),
        sa.Column("widget_type", sa.String(30), nullable=False),
        sa.Column("position_x", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position_y", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("config_json", sa.JSON()),
        sa.CheckConstraint("widget_type IN ('KPI','LINE_CHART','BAR_CHART','PIE_CHART','TABLE','ALERT_LIST','NUMBER')", name="ck_widget_type"),
        sa.CheckConstraint("position_x >= 0 AND position_y >= 0 AND width > 0 AND height > 0", name="ck_widget_geometry"),
    )
    op.create_table(
        "executive_report_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False, server_default="DAILY"),
        sa.Column("sales_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("gross_profit", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("receivables_open", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("payables_open", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("cash_in", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("cash_out", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("inventory_value", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("production_quantity", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("shortage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("period_end >= period_start", name="ck_exec_report_period"),
        sa.CheckConstraint("report_type IN ('DAILY','WEEKLY','MONTHLY','QUARTERLY','CUSTOM')", name="ck_exec_report_type"),
        sa.UniqueConstraint("report_date", "period_start", "period_end", "report_type", name="uq_exec_report_snapshot"),
    )
    op.create_index("idx_kpi_values_kpi_period", "kpi_values", ["kpi_id", "period_end"])
    op.create_index("idx_widgets_dashboard_position", "dashboard_widgets", ["dashboard_id", "position_y", "position_x"])
    op.create_index("idx_exec_report_date_type", "executive_report_snapshots", ["report_date", "report_type"])


def downgrade():
    op.drop_index("idx_exec_report_date_type", table_name="executive_report_snapshots")
    op.drop_index("idx_widgets_dashboard_position", table_name="dashboard_widgets")
    op.drop_index("idx_kpi_values_kpi_period", table_name="kpi_values")
    op.drop_table("executive_report_snapshots")
    op.drop_table("dashboard_widgets")
    op.drop_table("dashboards")
    op.drop_table("kpi_values")
    op.drop_table("kpi_definitions")
