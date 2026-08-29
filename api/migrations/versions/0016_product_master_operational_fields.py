"""E.Y.T ERP operational Product Master fields"""
from alembic import op
import sqlalchemy as sa
revision="0016"; down_revision="0015"; branch_labels=None; depends_on=None
def upgrade():
    for name,col in [("oem_code",sa.Column("oem_code",sa.String(120))), ("brand",sa.Column("brand",sa.String(120))), ("material",sa.Column("material",sa.String(120))), ("weight_kg",sa.Column("weight_kg",sa.Numeric(12,4))), ("cost_price",sa.Column("cost_price",sa.Numeric(18,4),nullable=False,server_default="0")), ("sale_price",sa.Column("sale_price",sa.Numeric(18,4),nullable=False,server_default="0")), ("min_stock",sa.Column("min_stock",sa.Numeric(18,6),nullable=False,server_default="0")), ("is_sellable",sa.Column("is_sellable",sa.Boolean(),nullable=False,server_default=sa.true())), ("is_purchasable",sa.Column("is_purchasable",sa.Boolean(),nullable=False,server_default=sa.true())), ("image_url",sa.Column("image_url",sa.Text()))]: op.add_column("products",col)
    op.create_index("idx_products_oem_code","products",["oem_code"]); op.create_index("idx_products_brand","products",["brand"])
def downgrade():
    op.drop_index("idx_products_brand",table_name="products"); op.drop_index("idx_products_oem_code",table_name="products")
    for c in ["image_url","is_purchasable","is_sellable","min_stock","sale_price","cost_price","weight_kg","material","brand","oem_code"]: op.drop_column("products",c)
