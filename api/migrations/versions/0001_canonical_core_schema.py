"""E.Y.T ERP canonical core schema

Revision ID: 0001
Reconciles the foundation tables required by later ERP modules.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "customers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_code", sa.String(80), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(250), nullable=False),
        sa.Column("customer_type", sa.String(40)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "suppliers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("supplier_code", sa.String(80), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(250), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "product_categories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name_fa", sa.String(200), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("product_categories.id")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sku", sa.String(100), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(250), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("product_categories.id")),
        sa.Column("unit", sa.String(30), nullable=False, server_default="PCS"),
        sa.Column("barcode", sa.String(100), unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "warehouses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade():
    op.drop_table("warehouses")
    op.drop_table("products")
    op.drop_table("product_categories")
    op.drop_table("suppliers")
    op.drop_table("customers")
    op.drop_table("roles")
