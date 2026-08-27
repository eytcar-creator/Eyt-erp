"""E.Y.T ERP warranty, installation verification and claims

Revision ID: 0012
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "warranties",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("warranty_no", sa.String(80), nullable=False, unique=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT")),
        sa.Column("sales_order_id", UUID(as_uuid=True), sa.ForeignKey("sales_orders.id", ondelete="RESTRICT")),
        sa.Column("delivery_id", UUID(as_uuid=True), sa.ForeignKey("deliveries.id", ondelete="RESTRICT")),
        sa.Column("serial_no", sa.String(120), unique=True),
        sa.Column("warranty_code", sa.String(120), unique=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("end_date >= start_date", name="ck_warranty_dates"),
        sa.CheckConstraint("status IN ('ACTIVE','EXPIRED','VOID','CLAIMED')", name="ck_warranty_status"),
    )
    op.create_table(
        "installation_verifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("verification_no", sa.String(80), nullable=False, unique=True),
        sa.Column("warranty_id", UUID(as_uuid=True), sa.ForeignKey("warranties.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("vehicle_model_id", UUID(as_uuid=True), sa.ForeignKey("vehicle_models.id", ondelete="RESTRICT")),
        sa.Column("installer_name", sa.String(200)),
        sa.Column("installer_mobile", sa.String(40)),
        sa.Column("vehicle_vin", sa.String(80)),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("verification_method", sa.String(20), nullable=False, server_default="QR"),
        sa.Column("status", sa.String(20), nullable=False, server_default="VERIFIED"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("verification_method IN ('QR','BARCODE','MANUAL')", name="ck_install_verification_method"),
        sa.CheckConstraint("status IN ('PENDING','VERIFIED','REJECTED','REVOKED')", name="ck_install_verification_status"),
    )
    op.create_table(
        "warranty_claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_no", sa.String(80), nullable=False, unique=True),
        sa.Column("warranty_id", UUID(as_uuid=True), sa.ForeignKey("warranties.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("installation_verification_id", UUID(as_uuid=True), sa.ForeignKey("installation_verifications.id", ondelete="RESTRICT")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT")),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False, server_default="1"),
        sa.Column("reason_code", sa.String(60), nullable=False),
        sa.Column("status", sa.String(25), nullable=False, server_default="OPEN"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution", sa.String(40)),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("quantity > 0", name="ck_claim_quantity_positive"),
        sa.CheckConstraint("status IN ('OPEN','INVESTIGATING','APPROVED','REJECTED','REPLACED','CLOSED')", name="ck_claim_status"),
        sa.CheckConstraint("resolution IS NULL OR resolution IN ('REPAIR','REPLACE','CREDIT','REJECT','NO_FAULT')", name="ck_claim_resolution"),
    )
    op.create_index("idx_warranty_customer_status", "warranties", ["customer_id", "status"])
    op.create_index("idx_warranty_end_date", "warranties", ["end_date", "status"])
    op.create_index("idx_install_warranty", "installation_verifications", ["warranty_id"])
    op.create_index("idx_claim_status_opened", "warranty_claims", ["status", "opened_at"])


def downgrade():
    op.drop_index("idx_claim_status_opened", table_name="warranty_claims")
    op.drop_index("idx_install_warranty", table_name="installation_verifications")
    op.drop_index("idx_warranty_end_date", table_name="warranties")
    op.drop_index("idx_warranty_customer_status", table_name="warranties")
    op.drop_table("warranty_claims")
    op.drop_table("installation_verifications")
    op.drop_table("warranties")
