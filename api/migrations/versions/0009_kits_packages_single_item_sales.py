"""E.Y.T ERP kits, packages and single-item sales

Revision ID: 0009
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_kits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kit_sku", sa.String(100), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(250), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "kit_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kit_id", UUID(as_uuid=True), sa.ForeignKey("product_kits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False, server_default="1"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("quantity > 0", name="ck_kit_item_positive"),
        sa.UniqueConstraint("kit_id", "product_id", name="uq_kit_product"),
    )
    op.create_table(
        "kit_fitments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kit_id", UUID(as_uuid=True), sa.ForeignKey("product_kits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_model_id", UUID(as_uuid=True), sa.ForeignKey("vehicle_models.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("kit_id", "vehicle_model_id", name="uq_kit_vehicle"),
    )
    op.create_table(
        "sales_item_modes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT")),
        sa.Column("kit_id", UUID(as_uuid=True), sa.ForeignKey("product_kits.id", ondelete="RESTRICT")),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("mode IN ('SINGLE','KIT')", name="ck_sales_item_mode"),
        sa.CheckConstraint("(mode = 'SINGLE' AND product_id IS NOT NULL AND kit_id IS NULL) OR (mode = 'KIT' AND kit_id IS NOT NULL AND product_id IS NULL)", name="ck_sales_item_mode_target"),
        sa.UniqueConstraint("product_id", "kit_id", "mode", name="uq_sales_item_mode"),
    )
    op.create_index("idx_kit_fitments_vehicle", "kit_fitments", ["vehicle_model_id"])
    op.create_index("idx_kit_items_product", "kit_items", ["product_id"])
    op.create_index("idx_sales_item_modes_product", "sales_item_modes", ["product_id"])
    op.create_index("idx_sales_item_modes_kit", "sales_item_modes", ["kit_id"])


def downgrade():
    op.drop_index("idx_sales_item_modes_kit", table_name="sales_item_modes")
    op.drop_index("idx_sales_item_modes_product", table_name="sales_item_modes")
    op.drop_index("idx_kit_items_product", table_name="kit_items")
    op.drop_index("idx_kit_fitments_vehicle", table_name="kit_fitments")
    op.drop_table("sales_item_modes")
    op.drop_table("kit_fitments")
    op.drop_table("kit_items")
    op.drop_table("product_kits")
