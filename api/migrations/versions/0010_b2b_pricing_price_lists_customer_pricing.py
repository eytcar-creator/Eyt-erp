"""E.Y.T ERP B2B pricing, price lists and customer-specific pricing

Revision ID: 0010
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "price_lists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(60), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(200), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="IRR"),
        sa.Column("customer_segment", sa.String(40)),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="ck_price_list_dates"),
    )
    op.create_table(
        "price_list_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("price_list_id", UUID(as_uuid=True), sa.ForeignKey("price_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT")),
        sa.Column("kit_id", UUID(as_uuid=True), sa.ForeignKey("product_kits.id", ondelete="RESTRICT")),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("min_qty", sa.Numeric(18, 6), nullable=False, server_default="1"),
        sa.Column("max_qty", sa.Numeric(18, 6)),
        sa.CheckConstraint("(product_id IS NOT NULL) <> (kit_id IS NOT NULL)", name="ck_price_item_target"),
        sa.CheckConstraint("unit_price >= 0", name="ck_price_item_nonnegative"),
        sa.CheckConstraint("min_qty > 0", name="ck_price_item_min_positive"),
        sa.CheckConstraint("max_qty IS NULL OR max_qty >= min_qty", name="ck_price_item_qty_range"),
        sa.UniqueConstraint("price_list_id", "product_id", "kit_id", "min_qty", name="uq_price_list_item"),
    )
    op.create_table(
        "customer_price_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_list_id", UUID(as_uuid=True), sa.ForeignKey("price_lists.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="ck_assignment_dates"),
    )
    op.create_table(
        "customer_product_prices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("unit_price >= 0", name="ck_customer_price_nonnegative"),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="ck_customer_price_dates"),
        sa.UniqueConstraint("customer_id", "product_id", "valid_from", name="uq_customer_product_price_period"),
    )
    op.create_index("idx_price_items_product", "price_list_items", ["product_id"])
    op.create_index("idx_price_items_kit", "price_list_items", ["kit_id"])
    op.create_index("idx_customer_price_customer", "customer_price_assignments", ["customer_id", "priority"])
    op.create_index("idx_customer_product_price", "customer_product_prices", ["customer_id", "product_id"])


def downgrade():
    op.drop_index("idx_customer_product_price", table_name="customer_product_prices")
    op.drop_index("idx_customer_price_customer", table_name="customer_price_assignments")
    op.drop_index("idx_price_items_kit", table_name="price_list_items")
    op.drop_index("idx_price_items_product", table_name="price_list_items")
    op.drop_table("customer_product_prices")
    op.drop_table("customer_price_assignments")
    op.drop_table("price_list_items")
    op.drop_table("price_lists")
