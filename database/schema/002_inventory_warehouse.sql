-- E.Y.T ERP | Phase 2 Inventory & Warehouse Engine
-- PostgreSQL

CREATE TABLE IF NOT EXISTS warehouses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name_fa VARCHAR(200) NOT NULL,
    warehouse_type VARCHAR(30) NOT NULL DEFAULT 'STANDARD'
        CHECK (warehouse_type IN ('RAW_MATERIAL','WIP','FINISHED_GOODS','QUARANTINE','SUBCONTRACTOR','STANDARD')),
    location VARCHAR(250),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    code VARCHAR(80) NOT NULL,
    name_fa VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (warehouse_id, code)
);

CREATE TABLE IF NOT EXISTS inventory_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    location_id UUID REFERENCES warehouse_locations(id),
    product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
    reserved_quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
    quarantine_quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (warehouse_id, location_id, product_id)
);

CREATE TABLE IF NOT EXISTS inventory_lots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id),
    lot_number VARCHAR(100) NOT NULL,
    supplier_id UUID,
    received_at TIMESTAMPTZ,
    expiry_date DATE,
    unit_cost NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
    UNIQUE (product_id, lot_number)
);

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_no VARCHAR(80) NOT NULL UNIQUE,
    product_id UUID NOT NULL REFERENCES products(id),
    from_warehouse_id UUID REFERENCES warehouses(id),
    from_location_id UUID REFERENCES warehouse_locations(id),
    to_warehouse_id UUID REFERENCES warehouses(id),
    to_location_id UUID REFERENCES warehouse_locations(id),
    lot_id UUID REFERENCES inventory_lots(id),
    transaction_type VARCHAR(40) NOT NULL CHECK (transaction_type IN (
        'RECEIPT','ISSUE','TRANSFER','RESERVATION','RELEASE_RESERVATION',
        'PRODUCTION_CONSUMPTION','PRODUCTION_RECEIPT','SUBCONTRACT_SEND',
        'SUBCONTRACT_RETURN','ADJUSTMENT_IN','ADJUSTMENT_OUT','RETURN_RECEIPT',
        'QUARANTINE_IN','QUARANTINE_RELEASE','SCRAP'
    )),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    reference_type VARCHAR(50),
    reference_id UUID,
    reason TEXT,
    performed_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stock_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_no VARCHAR(80) NOT NULL UNIQUE,
    product_id UUID NOT NULL REFERENCES products(id),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    reference_type VARCHAR(50) NOT NULL,
    reference_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','RELEASED','CONSUMED','CANCELLED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS inventory_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    adjustment_no VARCHAR(80) NOT NULL UNIQUE,
    product_id UUID NOT NULL REFERENCES products(id),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    location_id UUID REFERENCES warehouse_locations(id),
    system_quantity NUMERIC(18,6) NOT NULL,
    physical_quantity NUMERIC(18,6) NOT NULL,
    variance_quantity NUMERIC(18,6) GENERATED ALWAYS AS (physical_quantity - system_quantity) STORED,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','APPROVED','REJECTED','POSTED')),
    requested_by UUID,
    approved_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_inventory_balances_product ON inventory_balances(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_product_date ON inventory_transactions(product_id, created_at);
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_reference ON inventory_transactions(reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_stock_reservations_reference ON stock_reservations(reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_stock_reservations_active ON stock_reservations(product_id, warehouse_id, status);
CREATE INDEX IF NOT EXISTS idx_inventory_adjustments_status ON inventory_adjustments(status);
