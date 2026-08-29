"""E.Y.T ERP production planning extensions.

Revision ID: 0015

BOM and production_order tables are canonicalized in 0004. This migration
extends the production model without recreating those tables.
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
    op.create_index("idx_work_orders_production_status", "work_orders", ["production_order_id", "status"])
    op.create_index("idx_outsourcing_supplier_status", "outsourcing_orders", ["supplier_id", "status"])


def downgrade():
    op.drop_index("idx_outsourcing_supplier_status", table_name="outsourcing_orders")
    op.drop_index("idx_work_orders_production_status", table_name="work_orders")
    op.drop_table("outsourcing_orders")
    op.drop_table("work_orders")
