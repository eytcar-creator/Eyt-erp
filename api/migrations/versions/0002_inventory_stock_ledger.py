"""E.Y.T ERP inventory and stock ledger

Revision ID: 0002
Reversible inventory foundation built on the canonical core schema.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_balances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("on_hand_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("reserved_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("reorder_point", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("on_hand_qty >= 0", name="ck_inventory_on_hand_nonnegative"),
        sa.CheckConstraint("reserved_qty >= 0 AND reserved_qty <= on_hand_qty", name="ck_inventory_reserved_valid"),
        sa.CheckConstraint("reorder_point >= 0", name="ck_inventory_reorder_nonnegative"),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
    )
    op.create_table(
        "inventory_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("transaction_no", sa.String(80), nullable=False, unique=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("reference_type", sa.String(50)),
        sa.Column("reference_id", UUID(as_uuid=True)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_tx_positive_qty"),
    )
    op.create_index("idx_inventory_balance_product", "inventory_balances", ["product_id"])
    op.create_index("idx_inventory_balance_warehouse", "inventory_balances", ["warehouse_id"])
    op.create_index("idx_inventory_tx_product_date", "inventory_transactions", ["product_id", "occurred_at"])
    op.create_index("idx_inventory_tx_reference", "inventory_transactions", ["reference_type", "reference_id"])


def downgrade():
    op.drop_index("idx_inventory_tx_reference", table_name="inventory_transactions")
    op.drop_index("idx_inventory_tx_product_date", table_name="inventory_transactions")
    op.drop_index("idx_inventory_balance_warehouse", table_name="inventory_balances")
    op.drop_index("idx_inventory_balance_product", table_name="inventory_balances")
    op.drop_table("inventory_transactions")
    op.drop_table("inventory_balances")
