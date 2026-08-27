-- E.Y.T ERP | Phase 5 Quality Control & Production Costing
-- PostgreSQL

CREATE TABLE IF NOT EXISTS quality_inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_no VARCHAR(80) NOT NULL UNIQUE,
    inspection_type VARCHAR(30) NOT NULL CHECK (inspection_type IN ('INCOMING','PROCESS','FINAL','RETURN')),
    product_id UUID NOT NULL REFERENCES products(id),
    production_order_id UUID REFERENCES production_orders(id),
    goods_receipt_id UUID REFERENCES goods_receipts(id),
    quantity_inspected NUMERIC(18,6) NOT NULL CHECK (quantity_inspected > 0),
    quantity_passed NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (quantity_passed >= 0),
    quantity_failed NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (quantity_failed >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','PASS','FAIL','HOLD','PARTIAL')),
    inspector_id UUID,
    inspected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS quality_inspection_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id UUID NOT NULL REFERENCES quality_inspections(id) ON DELETE CASCADE,
    characteristic_code VARCHAR(80) NOT NULL,
    characteristic_name_fa VARCHAR(200) NOT NULL,
    specification VARCHAR(250),
    measured_value VARCHAR(100),
    result VARCHAR(20) NOT NULL CHECK (result IN ('PASS','FAIL','NA')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS nonconformances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ncr_no VARCHAR(80) NOT NULL UNIQUE,
    inspection_id UUID REFERENCES quality_inspections(id),
    product_id UUID NOT NULL REFERENCES products(id),
    production_order_id UUID REFERENCES production_orders(id),
    severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    defect_code VARCHAR(80),
    defect_description TEXT NOT NULL,
    root_cause TEXT,
    corrective_action TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CONTAINED','CORRECTIVE_ACTION','VERIFIED','CLOSED')),
    owner_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS cost_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_order_id UUID NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    event_type VARCHAR(30) NOT NULL CHECK (event_type IN ('MATERIAL','LABOR','MACHINE','SUBCONTRACT','OVERHEAD','SCRAP','REWORK','OTHER')),
    reference_type VARCHAR(50),
    reference_id UUID,
    amount NUMERIC(18,4) NOT NULL CHECK (amount >= 0),
    quantity NUMERIC(18,6),
    event_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS production_cost_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_order_id UUID NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    planned_material_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    actual_material_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    labor_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    machine_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    subcontract_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    overhead_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    scrap_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    rework_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    total_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    good_quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
    unit_cost NUMERIC(18,6) NOT NULL DEFAULT 0,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (production_order_id)
);

CREATE INDEX IF NOT EXISTS idx_quality_inspections_product_status ON quality_inspections(product_id, status);
CREATE INDEX IF NOT EXISTS idx_quality_inspections_production ON quality_inspections(production_order_id);
CREATE INDEX IF NOT EXISTS idx_ncr_status_severity ON nonconformances(status, severity);
CREATE INDEX IF NOT EXISTS idx_ncr_product ON nonconformances(product_id);
CREATE INDEX IF NOT EXISTS idx_cost_events_production_type ON cost_events(production_order_id, event_type);
CREATE INDEX IF NOT EXISTS idx_cost_snapshots_product ON production_cost_snapshots(product_id, calculated_at);
