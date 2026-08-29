-- E.Y.T ERP | Migration 001 | Production core
-- PostgreSQL
-- Idempotent migration for the production domain.

BEGIN;

CREATE TABLE IF NOT EXISTS production_orders (
    id BIGSERIAL PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    product_code VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    target_qty NUMERIC(14,3) NOT NULL CHECK (target_qty > 0),
    order_date DATE NOT NULL,
    planned_start DATE,
    planned_end DATE,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    customer_id BIGINT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (planned_end IS NULL OR planned_start IS NULL OR planned_end >= planned_start)
);

CREATE TABLE IF NOT EXISTS material_lots (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    material_code VARCHAR(100) NOT NULL,
    material_name VARCHAR(255) NOT NULL,
    specification VARCHAR(255),
    diameter_mm NUMERIC(10,3),
    quantity NUMERIC(14,3) NOT NULL CHECK (quantity >= 0),
    unit VARCHAR(20) NOT NULL DEFAULT 'kg',
    supplier_name VARCHAR(255),
    purchase_cost NUMERIC(16,2) NOT NULL DEFAULT 0 CHECK (purchase_cost >= 0),
    received_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS production_operations (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    sequence_no INT NOT NULL CHECK (sequence_no > 0),
    operation_code VARCHAR(50) NOT NULL,
    operation_name VARCHAR(255) NOT NULL,
    contractor_name VARCHAR(255),
    planned_start DATE,
    planned_end DATE,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    input_qty NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (input_qty >= 0),
    accepted_qty NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (accepted_qty >= 0),
    rejected_qty NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (rejected_qty >= 0),
    waste_qty NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (waste_qty >= 0),
    waste_reason TEXT,
    service_cost NUMERIC(16,2) NOT NULL DEFAULT 0 CHECK (service_cost >= 0),
    transport_cost NUMERIC(16,2) NOT NULL DEFAULT 0 CHECK (transport_cost >= 0),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    notes TEXT,
    UNIQUE(production_order_id, sequence_no),
    CHECK (accepted_qty + rejected_qty + waste_qty = input_qty),
    CHECK (actual_end IS NULL OR actual_start IS NOT NULL),
    CHECK (planned_end IS NULL OR planned_start IS NULL OR planned_end >= planned_start)
);

CREATE TABLE IF NOT EXISTS quality_inspections (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    operation_id BIGINT REFERENCES production_operations(id) ON DELETE SET NULL,
    inspection_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    inspected_qty NUMERIC(14,3) NOT NULL CHECK (inspected_qty >= 0),
    accepted_qty NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (accepted_qty >= 0),
    rejected_qty NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (rejected_qty >= 0),
    result VARCHAR(20) NOT NULL,
    inspector_name VARCHAR(255),
    report_no VARCHAR(100),
    notes TEXT,
    CHECK (accepted_qty + rejected_qty = inspected_qty)
);

CREATE TABLE IF NOT EXISTS production_costs (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    cost_type VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    amount NUMERIC(16,2) NOT NULL CHECK (amount >= 0),
    incurred_date DATE,
    contractor_name VARCHAR(255),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS customer_prepayments (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    customer_id BIGINT,
    payment_date DATE NOT NULL,
    amount NUMERIC(16,2) NOT NULL CHECK (amount > 0),
    payment_method VARCHAR(50),
    reference_no VARCHAR(100),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS collections (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    customer_id BIGINT,
    due_date DATE,
    collection_date DATE,
    amount NUMERIC(16,2) NOT NULL CHECK (amount > 0),
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    reference_no VARCHAR(100),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS capital_holding_costs (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    capital_amount NUMERIC(16,2) NOT NULL CHECK (capital_amount >= 0),
    holding_days NUMERIC(14,3) NOT NULL CHECK (holding_days >= 0),
    annual_rate NUMERIC(8,5) NOT NULL CHECK (annual_rate >= 0),
    holding_cost NUMERIC(16,2) NOT NULL CHECK (holding_cost >= 0),
    calculation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS production_traceability (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    operation_id BIGINT REFERENCES production_operations(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_name VARCHAR(255),
    contractor_name VARCHAR(255),
    reference_no VARCHAR(100),
    document_path TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS production_alerts (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'open'
);

CREATE INDEX IF NOT EXISTS idx_prod_ops_order ON production_operations(production_order_id);
CREATE INDEX IF NOT EXISTS idx_material_lots_order ON material_lots(production_order_id);
CREATE INDEX IF NOT EXISTS idx_prod_costs_order ON production_costs(production_order_id);
CREATE INDEX IF NOT EXISTS idx_qc_order ON quality_inspections(production_order_id);
CREATE INDEX IF NOT EXISTS idx_trace_order_time ON production_traceability(production_order_id, event_time);
CREATE INDEX IF NOT EXISTS idx_alerts_open ON production_alerts(status, severity);

COMMIT;
