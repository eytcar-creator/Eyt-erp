CREATE TABLE IF NOT EXISTS document_intake_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES document_intake_items(id) ON DELETE CASCADE,
    line_no INTEGER NOT NULL CHECK (line_no > 0),
    raw_description TEXT,
    product_code VARCHAR(100),
    quantity NUMERIC(20,4) CHECK (quantity IS NULL OR quantity > 0),
    unit VARCHAR(30),
    unit_price NUMERIC(20,4) CHECK (unit_price IS NULL OR unit_price >= 0),
    discount_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    tax_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    line_total NUMERIC(20,2),
    match_status VARCHAR(20) NOT NULL DEFAULT 'UNMATCHED'
        CHECK (match_status IN ('UNMATCHED','MATCHED','REVIEW','BLOCKED')),
    match_confidence NUMERIC(5,4) CHECK (match_confidence IS NULL OR match_confidence BETWEEN 0 AND 1),
    extracted_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(document_id, line_no)
);

CREATE INDEX IF NOT EXISTS idx_document_intake_lines_document
    ON document_intake_line_items(document_id);

CREATE INDEX IF NOT EXISTS idx_document_intake_lines_product
    ON document_intake_line_items(product_code);

ALTER TABLE document_intake_items
    ADD COLUMN IF NOT EXISTS line_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS calculated_lines_total NUMERIC(20,2),
    ADD COLUMN IF NOT EXISTS arithmetic_variance NUMERIC(20,2);

COMMENT ON TABLE document_intake_line_items IS
'Extracted invoice lines used for deterministic SKU matching and arithmetic validation. It does not post inventory or finance records.';
