"""E.Y.T ERP operational Product Master fields

Revision ID: 0016
Extends the canonical product record used by sales, purchasing, inventory,
production, catalog and integrations.
"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("oem_code", sa.String(120)))
    op.add_column("products", sa.Column("brand", sa.String(120)))
    op.add_column("products", sa.Column("material", sa.String(120)))
    op.add_column("products", sa.Column("weight_kg", sa.Numeric(12, 4)))
    op.add_column("products", sa.Column("cost_price", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("sale_price", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("min_stock", sa.Numeric(18, 6), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("is_sellable", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("products", sa.Column("is_purchasable", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("products", sa.Column("image_url", sa.Text()))
    op.create_index("idx_products_oem_code", "products", ["oem_code"])
    op.create_index("idx_products_brand", "products", ["brand"])
    op.create_check_constraint("ck_products_weight_nonnegative", "products", "weight_kg IS NULL OR weight_kg >= 0")
    op.create_check_constraint("ck_products_prices_nonnegative", "products", "cost_price >= 0 AND sale_price >= 0")
    op.create_check_constraint("ck_products_min_stock_nonnegative", "products", "min_stock >= 0")


def downgrade():
    op.drop_constraint("ck_products_min_stock_nonnegative", "products", type_="check")
    op.drop_constraint("ck_products_prices_nonnegative", "products", type_="check")
    op.drop_constraint("ck_products_weight_nonnegative", "products", type_="check")
    op.drop_index("idx_products_brand", table_name="products")
    op.drop_index("idx_products_oem_code", table_name="products")
    op.drop_column("products", "image_url")
    op.drop_column("products", "is_purchasable")
    op.drop_column("products", "is_sellable")
    op.drop_column("products", "min_stock")
    op.drop_column("products", "sale_price")
    op.drop_column("products", "cost_price")
    op.drop_column("products", "weight_kg")
    op.drop_column("products", "material")
    op.drop_column("products", "brand")
    op.drop_column("products", "oem_code")
