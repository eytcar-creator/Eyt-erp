-- E.Y.T ERP production core schema
-- PostgreSQL-compatible baseline

CREATE TABLE IF NOT EXISTS production_orders (
    id BIGSERIAL PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    product_code VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    target_qty NUMERIC(14,3) NOT NULL,
    order_date DATE NOT NULL,
    planned_start DATE,
    planned_end DATE,
    actual_start TIMESTAMP,
    actual_end TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    customer_id BIGINT,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS material_lots (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
    material_code VARCHAR(100) NOT NULL,
    material_name VARCHAR(255) NOT NULL,
    specification VARCHAR(255),
    diameter_mm NUMERIC(10,3),
    quantity NUMERIC(14,3) NOT NULL,
    unit VARCHAR(20) NOT NULL DEFAULT 'kg',
    supplier_name VARCHAR(255),
    purchase_cost NUMERIC(16,2) DEFAULT 0,
    received_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS production_operations (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
    sequence_no INT NOT NULL,
    operation_code VARCHAR(50) NOT NULL,
    operation_name VARCHAR(255) NOT NULL,
    contractor_name VARCHAR(255),
    planned_start DATE,
    planned_end DATE,
    actual_start TIMESTAMP,
    actual_end TIMESTAMP,
    input_qty NUMERIC(14,3) DEFAULT 0,
    accepted_qty NUMERIC(14,3) DEFAULT 0,
    rejected_qty NUMERIC(14,3) DEFAULT 0,
    waste_qty NUMERIC(14,3) DEFAULT 0,
    waste_reason TEXT,
    service_cost NUMERIC(16,2) DEFAULT 0,
    transport_cost NUMERIC(16,2) DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    notes TEXT,
    UNIQUE(production_order_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS quality_inspections (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
    operation_id BIGINT REFERENCES production_operations(id),
    inspection_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    inspected_qty NUMERIC(14,3) NOT NULL,
    accepted_qty NUMERIC(14,3) DEFAULT 0,
    rejected_qty NUMERIC(14,3) DEFAULT 0,
    result VARCHAR(20) NOT NULL,
    inspector_name VARCHAR(255),
    report_no VARCHAR(100),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS production_costs (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
    cost_type VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    amount NUMERIC(16,2) NOT NULL DEFAULT 0,
    incurred_date DATE,
    contractor_name VARCHAR(255),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS customer_prepayments (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
    customer_id BIGINT,
    payment_date DATE NOT NULL,
    amount NUMERIC(16,2) NOT NULL,
    payment_method VARCHAR(50),
    reference_no VARCHAR(100),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS collections (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
    customer_id BIGINT,
    due_date DATE,
    collection_date DATE,
    amount NUMERIC(16,2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    reference_no VARCHAR(100),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS capital_holding_costs (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
    capital_amount NUMERIC(16,2) NOT NULL,
    holding_days NUMERIC(14,3) NOT NULL,
    annual_rate NUMERIC(8,5) NOT NULL DEFAULT 0,
    holding_cost NUMERIC(16,2) NOT NULL DEFAULT 0,
    calculation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS production_traceability (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
    operation_id BIGINT REFERENCES production_operations(id),
    event_type VARCHAR(50) NOT NULL,
    event_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_name VARCHAR(255),
    contractor_name VARCHAR(255),
    reference_no VARCHAR(100),
    document_path TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS production_alerts (
    id BIGSERIAL PRIMARY KEY,
    production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'open'
);
