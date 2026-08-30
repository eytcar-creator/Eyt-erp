"""E.Y.T ERP quality control, batch traceability and finished-goods release.

Revision ID: 0017
Revision chain: 0016 -> 0017
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quality_batches",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("batch_no", sa.String(100), nullable=False),
        sa.Column("production_order_no", sa.String(80), nullable=False),
        sa.Column("product_code", sa.String(100), nullable=False),
        sa.Column("planned_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="CREATED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("released_by", sa.String(100)),
        sa.UniqueConstraint("batch_no", name="uq_quality_batch_no"),
        sa.CheckConstraint("planned_qty > 0", name="ck_quality_batch_planned_positive"),
        sa.CheckConstraint("accepted_qty >= 0 AND rejected_qty >= 0", name="ck_quality_batch_results_nonnegative"),
        sa.CheckConstraint("accepted_qty + rejected_qty <= planned_qty", name="ck_quality_batch_results_not_over_plan"),
        sa.CheckConstraint("status IN ('CREATED','INSPECTION','PASSED','FAILED','BLOCKED','RELEASED')", name="ck_quality_batch_status"),
    )
    op.create_index("idx_quality_batch_order", "quality_batches", ["production_order_no", "product_code"])
    op.create_index("idx_quality_batch_status", "quality_batches", ["status", "created_at"])

    op.create_table(
        "quality_inspections",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("quality_batch_id", sa.BigInteger(), sa.ForeignKey("quality_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_type", sa.String(40), nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("inspector", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("result IN ('PASS','FAIL','CONDITIONAL')", name="ck_quality_inspection_result"),
    )
    op.create_index("idx_quality_inspection_batch", "quality_inspections", ["quality_batch_id", "inspected_at"])

    op.create_table(
        "quality_defects",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("quality_batch_id", sa.BigInteger(), sa.ForeignKey("quality_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("defect_code", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MAJOR"),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("quantity > 0", name="ck_quality_defect_qty_positive"),
        sa.CheckConstraint("severity IN ('MINOR','MAJOR','CRITICAL')", name="ck_quality_defect_severity"),
    )

    op.create_table(
        "finished_goods_releases",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("quality_batch_id", sa.BigInteger(), sa.ForeignKey("quality_batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_code", sa.String(100), nullable=False),
        sa.Column("warehouse_code", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("release_status", sa.String(20), nullable=False, server_default="RELEASED"),
        sa.Column("released_by", sa.String(100), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("quality_batch_id", name="uq_finished_goods_release_batch"),
        sa.CheckConstraint("quantity > 0", name="ck_finished_goods_release_qty_positive"),
        sa.CheckConstraint("release_status IN ('RELEASED','BLOCKED','REVERSED')", name="ck_finished_goods_release_status"),
    )

    op.create_table(
        "traceability_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("batch_no", sa.String(100), nullable=False),
        sa.Column("serial_no", sa.String(100)),
        sa.Column("product_code", sa.String(100), nullable=False),
        sa.Column("production_order_no", sa.String(80)),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("reference_type", sa.String(50)),
        sa.Column("reference_id", sa.String(100)),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("event_type IN ('CREATED','OPERATION','QC_INSPECTION','QC_PASS','QC_FAIL','RELEASE','SHIPMENT','RETURN','SCRAP')", name="ck_trace_event_type"),
    )
    op.create_index("idx_trace_batch", "traceability_events", ["batch_no", "event_at"])
    op.create_index("idx_trace_serial", "traceability_events", ["serial_no", "event_at"])
    op.create_index("idx_trace_product", "traceability_events", ["product_code", "event_at"])


def downgrade():
    op.drop_index("idx_trace_product", table_name="traceability_events")
    op.drop_index("idx_trace_serial", table_name="traceability_events")
    op.drop_index("idx_trace_batch", table_name="traceability_events")
    op.drop_table("traceability_events")
    op.drop_table("finished_goods_releases")
    op.drop_table("quality_defects")
    op.drop_index("idx_quality_inspection_batch", table_name="quality_inspections")
    op.drop_table("quality_inspections")
    op.drop_index("idx_quality_batch_status", table_name="quality_batches")
    op.drop_index("idx_quality_batch_order", table_name="quality_batches")
    op.drop_table("quality_batches")
