"""E.Y.T ERP Order Center schema reconciliation.

Revision ID: 0019
down_revision: 0018

This migration is the canonical Alembic bridge for the Order Center. It is
intentionally additive: older SQL baselines and the 0015+ Alembic segment may
already provide part of the schema, so existing columns/tables are preserved
and only missing compatibility fields/indexes are added.
"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return bool(bind.execute(sa.text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='public' AND table_name=:name
    """), {"name": name}).scalar())


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return bool(bind.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name=:table AND column_name=:column
    """), {"table": table, "column": column}).scalar())


def _add_column(table: str, column: str, definition: str) -> None:
    if _has_table(table) and not _has_column(table, column):
        op.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def upgrade():
    # sales_orders compatibility used by the production Order Center.
    if _has_table("sales_orders"):
        _add_column("sales_orders", "representative_id", "UUID")
        _add_column("sales_orders", "channel", "VARCHAR(40)")
        _add_column("sales_orders", "payment_type", "VARCHAR(20) NOT NULL DEFAULT 'CASH'")
        _add_column("sales_orders", "idempotency_key", "VARCHAR(160)")
        _add_column("sales_orders", "notes", "TEXT")
        _add_column("sales_orders", "confirmed_at", "TIMESTAMPTZ")
        _add_column("sales_orders", "updated_at", "TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP")
        op.execute(sa.text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_orders_idempotency_key
            ON sales_orders(idempotency_key) WHERE idempotency_key IS NOT NULL
        """))

    if _has_table("sales_order_items"):
        _add_column("sales_order_items", "cost_snapshot", "NUMERIC(18,6)")
        _add_column("sales_order_items", "contribution", "NUMERIC(20,6)")

    # Reservation compatibility: support both the historical qty/product_id
    # baseline and the canonical product_code/quantity Order Center contract.
    if not _has_table("inventory_reservations"):
        op.create_table(
            "inventory_reservations",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
            sa.Column("document_no", sa.String(80), nullable=False),
            sa.Column("warehouse_code", sa.String(60), nullable=False),
            sa.Column("product_code", sa.String(100), nullable=False),
            sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="RESERVED"),
            sa.Column("reference_type", sa.String(40)),
            sa.Column("reference_id", sa.String(100)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("consumed_at", sa.DateTime(timezone=True)),
        )
    else:
        _add_column("inventory_reservations", "document_no", "VARCHAR(80)")
        _add_column("inventory_reservations", "warehouse_code", "VARCHAR(60)")
        _add_column("inventory_reservations", "product_code", "VARCHAR(100)")
        _add_column("inventory_reservations", "quantity", "NUMERIC(18,6)")
        _add_column("inventory_reservations", "reference_type", "VARCHAR(40)")
        _add_column("inventory_reservations", "reference_id", "VARCHAR(100)")
        _add_column("inventory_reservations", "consumed_at", "TIMESTAMPTZ")
        if _has_column("inventory_reservations", "qty"):
            op.execute(sa.text("UPDATE inventory_reservations SET quantity=qty WHERE quantity IS NULL"))
        if _has_column("inventory_reservations", "order_no"):
            op.execute(sa.text("UPDATE inventory_reservations SET document_no=order_no WHERE document_no IS NULL"))
        if _has_column("inventory_reservations", "product_id") and _has_table("products"):
            op.execute(sa.text("""
                UPDATE inventory_reservations r
                SET product_code=p.product_code
                FROM products p
                WHERE r.product_id=p.id AND r.product_code IS NULL
            """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_inventory_reservations_stock
        ON inventory_reservations(warehouse_code, product_code, status)
    """))

    # Credit/audit tables required by atomic confirmation.
    if not _has_table("customer_credit_profiles"):
        op.create_table(
            "customer_credit_profiles",
            sa.Column("customer_id", sa.UUID(), primary_key=True),
            sa.Column("credit_limit", sa.Numeric(18,4), nullable=False, server_default="0"),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="NORMAL"),
            sa.Column("manual_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    if not _has_table("order_credit_checks"):
        op.create_table(
            "order_credit_checks",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
            sa.Column("order_no", sa.String(60), nullable=False),
            sa.Column("customer_id", sa.UUID(), nullable=False),
            sa.Column("requested_amount", sa.Numeric(18,4), nullable=False),
            sa.Column("allowed", sa.Boolean(), nullable=False),
            sa.Column("credit_status", sa.String(30), nullable=False),
            sa.Column("available_credit", sa.Numeric(18,4), nullable=False),
            sa.Column("reason", sa.String(120)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    if not _has_table("order_audit_log"):
        op.create_table(
            "order_audit_log",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
            sa.Column("order_no", sa.String(60), nullable=False),
            sa.Column("event_type", sa.String(80), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )


def downgrade():
    # Compatibility migration is deliberately non-destructive. Rollback of
    # historical baseline objects must be owned by the migration that created them.
    pass
