CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS document_intake_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(120) NOT NULL,
    storage_path TEXT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes > 0),
    source_channel VARCHAR(30) NOT NULL DEFAULT 'UPLOAD',
    document_type VARCHAR(40),
    status VARCHAR(20) NOT NULL DEFAULT 'RECEIVED'
        CHECK (status IN ('RECEIVED','EXTRACTING','EXTRACTED','REVIEW','READY_TO_POST','POSTED','BLOCKED','FAILED')),
    supplier_code VARCHAR(60),
    invoice_no VARCHAR(100),
    invoice_date DATE,
    due_date DATE,
    currency VARCHAR(10) DEFAULT 'IRR',
    subtotal NUMERIC(20,2),
    discount_amount NUMERIC(20,2),
    tax_amount NUMERIC(20,2),
    total_amount NUMERIC(20,2),
    extraction_confidence NUMERIC(5,4) CHECK (extraction_confidence IS NULL OR extraction_confidence BETWEEN 0 AND 1),
    extracted_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    posted_reference_type VARCHAR(60),
    posted_reference_id VARCHAR(120),
    created_by UUID REFERENCES eyt_users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    extracted_at TIMESTAMPTZ,
    posted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_document_intake_sha256
    ON document_intake_items(sha256);

CREATE INDEX IF NOT EXISTS idx_document_intake_status_created
    ON document_intake_items(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_intake_supplier_invoice
    ON document_intake_items(supplier_code, invoice_no);

CREATE TABLE IF NOT EXISTS document_intake_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES document_intake_items(id) ON DELETE CASCADE,
    event_type VARCHAR(40) NOT NULL,
    actor_user_id UUID REFERENCES eyt_users(id),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_document_intake_events_document
    ON document_intake_events(document_id, created_at);

COMMENT ON TABLE document_intake_items IS
'Inbound document gateway. Stores the original document reference and extracted/validated metadata. It is an intake layer, not a replacement for ERP source-of-truth modules.';

COMMENT ON COLUMN document_intake_items.extracted_data IS
'Structured OCR/AI extraction payload. The original file remains the audit source.';

COMMENT ON COLUMN document_intake_items.validation_errors IS
'Machine validation findings preventing safe automatic posting.';
