-- E.Y.T ERP | Migration 007 | QC Release + Batch Traceability
-- PostgreSQL / idempotent
BEGIN;

CREATE TABLE IF NOT EXISTS quality_batches (
    id BIGSERIAL PRIMARY KEY,
    batch_no VARCHAR(100) NOT NULL UNIQUE,
    production_order_no VARCHAR(80) NOT NULL,
    product_code VARCHAR(100) NOT NULL REFERENCES products(product_code),
    planned_qty NUMERIC(18,6) NOT NULL CHECK (planned_qty > 0),
    accepted_qty NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (accepted_qty >= 0),
    rejected_qty NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (rejected_qty >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'CREATED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at TIMESTAMPTZ,
    released_by VARCHAR(100),
    CHECK (accepted_qty + rejected_qty <= planned_qty),
    CHECK (status IN ('CREATED','INSPECTION','PASSED','FAILED','BLOCKED','RELEASED'))
);

CREATE TABLE IF NOT EXISTS quality_defects (
    id BIGSERIAL PRIMARY KEY,
    quality_batch_id BIGINT NOT NULL REFERENCES quality_batches(id) ON DELETE CASCADE,
    defect_code VARCHAR(50) NOT NULL,
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    severity VARCHAR(20) NOT NULL DEFAULT 'MAJOR',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (severity IN ('MINOR','MAJOR','CRITICAL'))
);

CREATE TABLE IF NOT EXISTS finished_goods_releases (
    id BIGSERIAL PRIMARY KEY,
    quality_batch_id BIGINT NOT NULL REFERENCES quality_batches(id) ON DELETE RESTRICT,
    product_code VARCHAR(100) NOT NULL REFERENCES products(product_code),
    warehouse_code VARCHAR(60) NOT NULL REFERENCES warehouses(code),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    release_status VARCHAR(20) NOT NULL DEFAULT 'RELEASED',
    released_by VARCHAR(100) NOT NULL,
    released_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(quality_batch_id),
    CHECK (release_status IN ('RELEASED','BLOCKED','REVERSED'))
);

CREATE TABLE IF NOT EXISTS traceability_events (
    id BIGSERIAL PRIMARY KEY,
    batch_no VARCHAR(100) NOT NULL,
    serial_no VARCHAR(100),
    product_code VARCHAR(100) NOT NULL REFERENCES products(product_code),
    production_order_no VARCHAR(80),
    event_type VARCHAR(40) NOT NULL,
    reference_type VARCHAR(50),
    reference_id VARCHAR(100),
    actor VARCHAR(100) NOT NULL,
    event_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    CHECK (event_type IN ('CREATED','OPERATION','QC_INSPECTION','QC_PASS','QC_FAIL','RELEASE','SHIPMENT','RETURN','SCRAP'))
);

CREATE INDEX IF NOT EXISTS idx_quality_batch_order ON quality_batches(production_order_no,product_code);
CREATE INDEX IF NOT EXISTS idx_quality_batch_status ON quality_batches(status,created_at);
CREATE INDEX IF NOT EXISTS idx_quality_defect_batch ON quality_defects(quality_batch_id);
CREATE INDEX IF NOT EXISTS idx_fg_release_product_warehouse ON finished_goods_releases(product_code,warehouse_code,release_status);
CREATE INDEX IF NOT EXISTS idx_trace_batch ON traceability_events(batch_no,event_at);
CREATE INDEX IF NOT EXISTS idx_trace_product ON traceability_events(product_code,event_at);

COMMIT;
