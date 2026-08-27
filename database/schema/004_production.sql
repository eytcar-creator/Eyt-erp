-- E.Y.T ERP | Phase 4 Production & BOM Execution Engine
-- PostgreSQL

CREATE TABLE IF NOT EXISTS production_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mo_no VARCHAR(80) NOT NULL UNIQUE,
    product_id UUID NOT NULL REFERENCES products(id),
    bom_id UUID REFERENCES boms(id),
    planned_quantity NUMERIC(18,6) NOT NULL CHECK (planned_quantity > 0),
    completed_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (completed_quantity >= 0),
    scrap_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (scrap_quantity >= 0),
    rework_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (rework_quantity >= 0),
    status VARCHAR(25) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','RELEASED','MATERIAL_SHORTAGE','IN_PROGRESS','ON_HOLD','QC_HOLD','COMPLETED','CANCELLED')),
    priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL'
        CHECK (priority IN ('LOW','NORMAL','HIGH','URGENT')),
    planned_start DATE,
    planned_finish DATE,
    actual_start TIMESTAMPTZ,
    actual_finish TIMESTAMPTZ,
    warehouse_id UUID REFERENCES warehouses(id),
    created_by UUID,
    released_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS production_order_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_order_id UUID NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    component_product_id UUID NOT NULL REFERENCES products(id),
    required_quantity NUMERIC(18,6) NOT NULL CHECK (required_quantity > 0),
    issued_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (issued_quantity >= 0),
    returned_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (returned_quantity >= 0),
    warehouse_id UUID REFERENCES warehouses(id),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN','PARTIAL','ISSUED','CLOSED'))
);

CREATE TABLE IF NOT EXISTS production_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_order_id UUID NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    sequence_no INTEGER NOT NULL,
    operation_code VARCHAR(80) NOT NULL,
    operation_name_fa VARCHAR(200) NOT NULL,
    work_center VARCHAR(120),
    operation_type VARCHAR(30) NOT NULL DEFAULT 'INTERNAL'
        CHECK (operation_type IN ('INTERNAL','SUBCONTRACTOR','ASSEMBLY','QC')),
    planned_quantity NUMERIC(18,6) NOT NULL CHECK (planned_quantity > 0),
    completed_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (completed_quantity >= 0),
    scrap_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (scrap_quantity >= 0),
    rework_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (rework_quantity >= 0),
    planned_minutes NUMERIC(18,3),
    actual_minutes NUMERIC(18,3),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','READY','IN_PROGRESS','ON_HOLD','COMPLETED','CANCELLED')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    notes TEXT,
    UNIQUE (production_order_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS production_operation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation_id UUID NOT NULL REFERENCES production_operations(id) ON DELETE CASCADE,
    log_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    quantity_completed NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (quantity_completed >= 0),
    scrap_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (scrap_quantity >= 0),
    rework_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (rework_quantity >= 0),
    downtime_minutes NUMERIC(18,3) NOT NULL DEFAULT 0 CHECK (downtime_minutes >= 0),
    downtime_reason TEXT,
    operator_id UUID,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS subcontractor_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subcontract_no VARCHAR(80) NOT NULL UNIQUE,
    production_order_id UUID REFERENCES production_orders(id),
    operation_id UUID REFERENCES production_operations(id),
    supplier_id UUID NOT NULL REFERENCES suppliers(id),
    sent_quantity NUMERIC(18,6) NOT NULL CHECK (sent_quantity > 0),
    returned_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (returned_quantity >= 0),
    approved_scrap_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (approved_scrap_quantity >= 0),
    rejected_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (rejected_quantity >= 0),
    unit_cost NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expected_return_date DATE,
    actual_return_date DATE,
    status VARCHAR(25) NOT NULL DEFAULT 'SENT'
        CHECK (status IN ('SENT','PARTIAL_RETURN','RETURNED','QC_HOLD','CLOSED','CANCELLED')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS production_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_no VARCHAR(80) NOT NULL UNIQUE,
    production_order_id UUID NOT NULL REFERENCES production_orders(id),
    product_id UUID NOT NULL REFERENCES products(id),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    qc_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (qc_status IN ('PENDING','PASS','FAIL','HOLD')),
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    received_by UUID,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_production_orders_product_status ON production_orders(product_id, status);
CREATE INDEX IF NOT EXISTS idx_production_orders_dates ON production_orders(planned_start, planned_finish, status);
CREATE INDEX IF NOT EXISTS idx_production_materials_product ON production_order_materials(component_product_id);
CREATE INDEX IF NOT EXISTS idx_production_operations_status ON production_operations(status, work_center);
CREATE INDEX IF NOT EXISTS idx_operation_logs_operation_time ON production_operation_logs(operation_id, log_time);
CREATE INDEX IF NOT EXISTS idx_subcontractor_orders_supplier_status ON subcontractor_orders(supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_subcontractor_orders_expected ON subcontractor_orders(expected_return_date, status);
CREATE INDEX IF NOT EXISTS idx_production_receipts_order ON production_receipts(production_order_id);
