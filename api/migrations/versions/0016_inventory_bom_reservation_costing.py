"""E.Y.T ERP inventory, BOM, reservation and costing extensions.

Revision ID: 0016
Revision chain: 0015 -> 0016

The canonical inventory and reservation tables already exist in the
production baseline migration (0004 in the historical Alembic chain / the
current SQL baseline). This revision therefore extends that baseline instead
of attempting to recreate the same tables, which would fail on an initialized
operational database.
"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bom_versions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("bom_code", sa.String(100), nullable=False),
        sa.Column("product_code", sa.String(100), nullable=False),
        sa.Column("version", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("bom_code", "version", name="uq_bom_code_version"),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','OBSOLETE')", name="ck_bom_status"),
    )
    op.create_table(
        "bom_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("bom_version_id", sa.BigInteger(), sa.ForeignKey("bom_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_code", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False, server_default="PCS"),
        sa.Column("scrap_percent", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.CheckConstraint("quantity > 0", name="ck_bom_item_qty_positive"),
        sa.CheckConstraint("scrap_percent >= 0 AND scrap_percent <= 100", name="ck_bom_item_scrap_range"),
    )
    op.create_table(
        "production_costs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("production_order_no", sa.String(80), nullable=False),
        sa.Column("material_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("operation_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("contractor_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("scrap_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("direct_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("production_order_no", name="uq_production_cost_order"),
    )


def downgrade():
    op.drop_table("production_costs")
    op.drop_table("bom_items")
    op.drop_table("bom_versions")
