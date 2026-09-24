-- E.Y.T ERP | Month-end inventory control foundation
-- Canonical inventory ledger remains the source of truth.
BEGIN;

CREATE TABLE IF NOT EXISTS inventory_month_end_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    warehouse_code VARCHAR(60) NOT NULL,
    product_code VARCHAR(100) NOT NULL,
    physical_qty NUMERIC(18,6) NOT NULL CHECK (physical_qty >= 0),
    reserved_qty NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
    qc_hold_qty NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (qc_hold_qty >= 0),
    sellable_qty NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (sellable_qty >= 0),
    unit_cost NUMERIC(20,6) NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
    inventory_value NUMERIC(22,6) NOT NULL DEFAULT 0 CHECK (inventory_value >= 0),
    valuation_method VARCHAR(30) NOT NULL DEFAULT 'MOVING_AVERAGE',
    source_cutoff_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN','RECONCILED','CLOSED')),
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(snapshot_date, warehouse_code, product_code)
);

CREATE TABLE IF NOT EXISTS inventory_stock_counts (
    id BIGSERIAL PRIMARY KEY,
    snapshot_id BIGINT NOT NULL REFERENCES inventory_month_end_snapshots(id) ON DELETE CASCADE,
    counted_qty NUMERIC(18,6) NOT NULL CHECK (counted_qty >= 0),
    system_qty NUMERIC(18,6) NOT NULL CHECK (system_qty >= 0),
    variance_qty NUMERIC(18,6) NOT NULL,
    variance_value NUMERIC(22,6) NOT NULL DEFAULT 0,
    reason_code VARCHAR(50),
    notes TEXT,
    counted_by VARCHAR(100),
    approved_by VARCHAR(100),
    counted_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'COUNTED'
        CHECK (status IN ('COUNTED','REVIEW','APPROVED','REJECTED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_inventory_snapshot_date
 ON inventory_month_end_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS ix_inventory_snapshot_product
 ON inventory_month_end_snapshots(product_code, snapshot_date);
CREATE INDEX IF NOT EXISTS ix_inventory_snapshot_warehouse
 ON inventory_month_end_snapshots(warehouse_code, snapshot_date);
CREATE INDEX IF NOT EXISTS ix_inventory_count_snapshot
 ON inventory_stock_counts(snapshot_id, status);

COMMIT;