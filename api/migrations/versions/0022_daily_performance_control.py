"""Daily planning and operational control layer.

Revision ID: 0022
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "performance_daily_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("location_code", sa.String(80), nullable=False),
        sa.Column("employee_code", sa.String(100)),
        sa.Column("operation_code", sa.String(100)),
        sa.Column("work_center", sa.String(120)),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="SET NULL")),
        sa.Column("product_code", sa.String(120)),
        sa.Column("planned_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("planned_hours", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("planned_qty >= 0", name="ck_perf_plan_qty_nonnegative"),
        sa.CheckConstraint("planned_hours >= 0", name="ck_perf_plan_hours_nonnegative"),
        sa.CheckConstraint("status IN ('PLANNED','IN_PROGRESS','DONE','BLOCKED','CANCELLED')", name="ck_perf_plan_status"),
    )
    op.create_index(
        "idx_perf_plan_date_location",
        "performance_daily_plans",
        ["plan_date", "location_code", "status"],
    )
    op.create_index(
        "idx_perf_plan_employee_date",
        "performance_daily_plans",
        ["employee_code", "plan_date"],
    )

    op.create_table(
        "performance_control_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("location_code", sa.String(80), nullable=False),
        sa.Column("employee_code", sa.String(100)),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("operation_code", sa.String(100)),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="SET NULL")),
        sa.Column("minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("reason_code", sa.String(80)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("event_type IN ('DOWNTIME','MATERIAL_SHORTAGE','ORDER_DELAY','OTHER')", name="ck_perf_event_type"),
        sa.CheckConstraint("minutes >= 0", name="ck_perf_event_minutes_nonnegative"),
        sa.CheckConstraint("quantity >= 0", name="ck_perf_event_qty_nonnegative"),
    )
    op.create_index(
        "idx_perf_event_date_type",
        "performance_control_events",
        ["event_date", "event_type", "location_code"],
    )


def downgrade():
    op.drop_index("idx_perf_event_date_type", table_name="performance_control_events")
    op.drop_table("performance_control_events")
    op.drop_index("idx_perf_plan_employee_date", table_name="performance_daily_plans")
    op.drop_index("idx_perf_plan_date_location", table_name="performance_daily_plans")
    op.drop_table("performance_daily_plans")
