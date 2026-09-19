-- E.Y.T ERP | Migration 028 | Order Center + Inventory reservation contract
-- Makes order confirmation and stock reservation share one canonical PostgreSQL contract.
BEGIN;

CREATE TABLE IF NOT EXISTS warehouses (
    code VARCHAR(60) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Legacy environments may already have warehouses with the older product-master shape.
-- Keep the canonical name contract additive so the migration chain works on both shapes.
ALTER TABLE warehouses
    ADD COLUMN IF NOT EXISTS name VARCHAR(200);
ALTER TABLE warehouses
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE warehouses
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

UPDATE warehouses
SET name = COALESCE(NULLIF(name, ''), code)
WHERE name IS NULL OR name = '';

-- Legacy product-master inventory uses name_fa instead of name.
UPDATE warehouses
SET name_fa = COALESCE(NULLIF(name_fa, ''), name, code)
WHERE name_fa IS NULL OR name_fa = '';

INSERT INTO warehouses(code, name, name_fa)
VALUES ('MAIN', 'انبار اصلی E.Y.T', 'انبار اصلی E.Y.T')
ON CONFLICT (code) DO NOTHING;

ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS representative_id UUID,
    ADD COLUMN IF NOT EXISTS channel VARCHAR(30) NOT NULL DEFAULT 'OTHER',
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(160),
    ADD COLUMN IF NOT EXISTS notes TEXT,
    ADD COLUMN IF NOT EXISTS payment_type VARCHAR(20) NOT NULL DEFAULT 'CASH',
    ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS ux_sales_orders_idempotency
    ON sales_orders(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid='sales_orders'::regclass
          AND contype='c'
          AND pg_get_constraintdef(oid) ILIKE '%status%'
    LOOP
        EXECUTE format('ALTER TABLE sales_orders DROP CONSTRAINT %I', r.conname);
    END LOOP;
END $$;

ALTER TABLE sales_orders
    ADD CONSTRAINT ck_sales_orders_status_eyt
    CHECK (status IN ('DRAFT','PENDING_CONFIRMATION','CONFIRMED','RESERVED','PREPARING','READY_TO_SHIP','SHIPPED','DELIVERED','FULFILLED','CANCELLED','RETURNED'));

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_no VARCHAR(100) NOT NULL,
    warehouse_code VARCHAR(60) NOT NULL REFERENCES warehouses(code),
    product_code VARCHAR(100) NOT NULL,
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(20) NOT NULL DEFAULT 'PCS',
    transaction_type VARCHAR(40) NOT NULL,
    reference_type VARCHAR(50),
    reference_id VARCHAR(120),
    unit_cost NUMERIC(20,6) NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_no VARCHAR(100) NOT NULL,
    warehouse_code VARCHAR(60) NOT NULL REFERENCES warehouses(code),
    product_code VARCHAR(100) NOT NULL,
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'RESERVED',
    reference_type VARCHAR(50),
    reference_id VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    consumed_at TIMESTAMPTZ,
    CHECK (status IN ('RESERVED','CONSUMED','CANCELLED'))
);

CREATE INDEX IF NOT EXISTS ix_inventory_tx_stock
    ON inventory_transactions(warehouse_code, product_code, created_at);
CREATE INDEX IF NOT EXISTS ix_inventory_reservation_stock
    ON inventory_reservations(warehouse_code, product_code, status);
CREATE INDEX IF NOT EXISTS ix_inventory_reservation_document
    ON inventory_reservations(document_no, product_code, status);

COMMIT;
