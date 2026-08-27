"""E.Y.T ERP quality control, NCR, quarantine and release

Revision ID: 0005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quality_inspections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("inspection_no", sa.String(80), nullable=False, unique=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="RESTRICT")),
        sa.Column("receipt_id", UUID(as_uuid=True), sa.ForeignKey("receipts.id", ondelete="RESTRICT")),
        sa.Column("inspected_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("status", sa.String(25), nullable=False, server_default="PENDING"),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("inspected_qty > 0", name="ck_qc_inspected_positive"),
        sa.CheckConstraint("accepted_qty >= 0 AND rejected_qty >= 0 AND accepted_qty + rejected_qty <= inspected_qty", name="ck_qc_disposition_valid"),
        sa.CheckConstraint("status IN ('PENDING','PASSED','FAILED','PARTIAL','CANCELLED')", name="ck_qc_status"),
    )
    op.create_table(
        "ncr_cases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ncr_no", sa.String(80), nullable=False, unique=True),
        sa.Column("inspection_id", UUID(as_uuid=True), sa.ForeignKey("quality_inspections.id", ondelete="RESTRICT")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("reason_code", sa.String(60), nullable=False),
        sa.Column("disposition", sa.String(30)),
        sa.Column("status", sa.String(25), nullable=False, server_default="OPEN"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("quantity > 0", name="ck_ncr_quantity_positive"),
        sa.CheckConstraint("status IN ('OPEN','INVESTIGATING','CORRECTIVE_ACTION','CLOSED','CANCELLED')", name="ck_ncr_status"),
        sa.CheckConstraint("disposition IS NULL OR disposition IN ('REWORK','SCRAP','RETURN','USE_AS_IS','REINSPECT')", name="ck_ncr_disposition"),
    )
    op.create_table(
        "quarantine_lots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lot_no", sa.String(80), nullable=False, unique=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ncr_id", UUID(as_uuid=True), sa.ForeignKey("ncr_cases.id", ondelete="RESTRICT")),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="QUARANTINED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("quantity > 0", name="ck_quarantine_quantity_positive"),
        sa.CheckConstraint("status IN ('QUARANTINED','RELEASED','REJECTED','SCRAPPED')", name="ck_quarantine_status"),
    )
    op.create_table(
        "quality_releases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("quarantine_lot_id", UUID(as_uuid=True), sa.ForeignKey("quarantine_lots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("released_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("released_qty > 0", name="ck_release_quantity_positive"),
    )
    op.create_index("idx_qc_product_date", "quality_inspections", ["product_id", "inspected_at"])
    op.create_index("idx_ncr_status", "ncr_cases", ["status"])
    op.create_index("idx_quarantine_status", "quarantine_lots", ["status"])


def downgrade():
    op.drop_index("idx_quarantine_status", table_name="quarantine_lots")
    op.drop_index("idx_ncr_status", table_name="ncr_cases")
    op.drop_index("idx_qc_product_date", table_name="quality_inspections")
    op.drop_table("quality_releases")
    op.drop_table("quarantine_lots")
    op.drop_table("ncr_cases")
    op.drop_table("quality_inspections")
