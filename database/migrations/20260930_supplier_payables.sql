BEGIN;
CREATE TABLE IF NOT EXISTS supplier_payables (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 supplier_id UUID NOT NULL REFERENCES eyt_suppliers(id),
 purchase_order_id UUID REFERENCES purchase_orders_v1(id),
 purchase_receipt_id UUID REFERENCES purchase_receipts_v1(id),
 document_id UUID UNIQUE REFERENCES document_intake_items(id),
 invoice_no VARCHAR(100) NOT NULL, invoice_date DATE, due_date DATE,
 currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
 invoice_amount NUMERIC(20,2) NOT NULL CHECK (invoice_amount >= 0),
 paid_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (paid_amount >= 0),
 outstanding_amount NUMERIC(20,2) GENERATED ALWAYS AS (invoice_amount-paid_amount) STORED,
 status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','PARTIAL','PAID','OVERDUE','BLOCKED')),
 funding_source VARCHAR(100), payment_terms TEXT,
 created_by UUID REFERENCES eyt_users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (paid_amount <= invoice_amount)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_supplier_payables_supplier_invoice ON supplier_payables(supplier_id,invoice_no);
CREATE INDEX IF NOT EXISTS idx_supplier_payables_due_status ON supplier_payables(due_date,status);
CREATE TABLE IF NOT EXISTS supplier_payable_events (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 payable_id UUID NOT NULL REFERENCES supplier_payables(id) ON DELETE CASCADE,
 event_type VARCHAR(40) NOT NULL, actor_user_id UUID REFERENCES eyt_users(id),
 amount NUMERIC(20,2), details JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_supplier_payable_events_payable ON supplier_payable_events(payable_id,created_at);
COMMIT;