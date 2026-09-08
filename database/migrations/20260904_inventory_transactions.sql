-- E.Y.T ERP: real inventory transaction engine
-- Idempotent PostgreSQL migration.
-- Reconciles the inventory ledger with legacy databases before creating indexes.

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id BIGSERIAL PRIMARY KEY,
    document_no VARCHAR(100) NOT NULL,
    warehouse_code VARCHAR(100) NOT NULL,
    product_code VARCHAR(100) NOT NULL,
    quantity NUMERIC(18,3) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(20) NOT NULL DEFAULT 'PCS',
    transaction_type VARCHAR(30) NOT NULL CHECK (transaction_type IN (
        'RECEIPT','RESERVE','ISSUE','PRODUCTION_RECEIPT','TRANSFER_IN',
        'TRANSFER_OUT','RETURN','CONSUMPTION','SCRAP','ADJUSTMENT'
    )),
    reference_type VARCHAR(50),
    reference_id VARCHAR(100),
    unit_cost NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Legacy/Alembic inventory ledgers may already have this table with a
-- different column contract. Extend it instead of recreating it.
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS document_no VARCHAR(100);
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS warehouse_code VARCHAR(100);
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS product_code VARCHAR(100);
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS quantity NUMERIC(18,3);
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS unit VARCHAR(20) DEFAULT 'PCS';
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(30);
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS reference_type VARCHAR(50);
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS reference_id VARCHAR(100);
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(18,2) DEFAULT 0;
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

UPDATE inventory_transactions
SET document_no = COALESCE(document_no, reference_id, 'LEGACY-' || id::text),
    unit = COALESCE(unit, 'PCS'),
    unit_cost = COALESCE(unit_cost, 0),
    created_at = COALESCE(created_at, CURRENT_TIMESTAMP)
WHERE document_no IS NULL OR unit IS NULL OR unit_cost IS NULL OR created_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_inventory_tx_stock
    ON inventory_transactions(product_code, warehouse_code, created_at, id);
CREATE INDEX IF NOT EXISTS idx_inventory_tx_document
    ON inventory_transactions(document_no);

CREATE TABLE IF NOT EXISTS inventory_reservations (
    id BIGSERIAL PRIMARY KEY,
    document_no VARCHAR(100) NOT NULL,
    warehouse_code VARCHAR(100) NOT NULL,
    product_code VARCHAR(100) NOT NULL,
    quantity NUMERIC(18,3) NOT NULL CHECK (quantity > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'RESERVED' CHECK (status IN ('RESERVED','CONSUMED','RELEASED')),
    reference_type VARCHAR(50),
    reference_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    consumed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inventory_reservation_stock
    ON inventory_reservations(product_code, warehouse_code, status, created_at, id);

-- Protect against accidental duplicate document posting for the same stock line/type.
CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_tx_document_line
    ON inventory_transactions(document_no, warehouse_code, product_code, transaction_type);

-- Audit is written through the existing EYT audit subsystem in the API.
