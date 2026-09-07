"""E.Y.T ERP Order Center schema contract.

Revision 0020
Revision chain: 0019 -> 0020

This migration makes the columns used by the production PostgreSQL order
adapter explicit and idempotent. It does not recreate canonical tables.
"""
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS product_code VARCHAR(100)")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS purchase_price NUMERIC(18,6) NOT NULL DEFAULT 0")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_products_product_code ON products(product_code) WHERE product_code IS NOT NULL")

    op.execute("ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS code VARCHAR(60)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_warehouses_code ON warehouses(code) WHERE code IS NOT NULL")

    op.execute("ALTER TABLE receivables ADD COLUMN IF NOT EXISTS outstanding NUMERIC(18,6) NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE receivables ADD COLUMN IF NOT EXISTS days_overdue INTEGER NOT NULL DEFAULT 0")

    op.execute("""CREATE TABLE IF NOT EXISTS representatives (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        representative_code VARCHAR(60) UNIQUE,
        name VARCHAR(200) NOT NULL,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")


def downgrade():
    # Contract columns are intentionally retained for safe rollback of the
    # application layer. Removing them could destroy operational data.
    pass
