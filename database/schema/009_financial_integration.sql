-- E.Y.T ERP | Phase 9 Financial Integration
-- PostgreSQL

CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_code VARCHAR(50) NOT NULL UNIQUE,
    account_name_fa VARCHAR(250) NOT NULL,
    account_type VARCHAR(30) NOT NULL CHECK (account_type IN ('ASSET','LIABILITY','EQUITY','REVENUE','COGS','EXPENSE','OTHER')),
    parent_id UUID REFERENCES chart_of_accounts(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS financial_journals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_no VARCHAR(80) NOT NULL UNIQUE,
    journal_date DATE NOT NULL DEFAULT CURRENT_DATE,
    source_type VARCHAR(50) NOT NULL,
    source_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','POSTED','VOID')),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    posted_at TIMESTAMPTZ,
    posted_by UUID
);

CREATE TABLE IF NOT EXISTS financial_journal_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id UUID NOT NULL REFERENCES financial_journals(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES chart_of_accounts(id),
    debit NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (debit >= 0),
    credit NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (credit >= 0),
    customer_id UUID REFERENCES customers(id),
    supplier_id UUID REFERENCES suppliers(id),
    reference_text VARCHAR(250),
    CHECK ((debit = 0 AND credit > 0) OR (credit = 0 AND debit > 0))
);

CREATE TABLE IF NOT EXISTS payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_no VARCHAR(80) NOT NULL UNIQUE,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('IN','OUT')),
    customer_id UUID REFERENCES customers(id),
    supplier_id UUID REFERENCES suppliers(id),
    invoice_id UUID REFERENCES sales_invoices(id),
    amount NUMERIC(18,4) NOT NULL CHECK (amount > 0),
    payment_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    payment_method VARCHAR(30) NOT NULL CHECK (payment_method IN ('BANK_TRANSFER','CASH','CARD','CHEQUE','OTHER')),
    bank_reference VARCHAR(120),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','CONFIRMED','REJECTED','REVERSED')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS cost_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_order_id UUID REFERENCES production_orders(id),
    source_type VARCHAR(50) NOT NULL,
    source_id UUID,
    cost_type VARCHAR(30) NOT NULL CHECK (cost_type IN ('MATERIAL','LABOR','MACHINE','SUBCONTRACT','OVERHEAD','SCRAP','REWORK','OTHER')),
    amount NUMERIC(18,4) NOT NULL CHECK (amount >= 0),
    allocated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS receivable_aging_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    snapshot_date DATE NOT NULL,
    current_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
    days_1_30 NUMERIC(18,4) NOT NULL DEFAULT 0,
    days_31_60 NUMERIC(18,4) NOT NULL DEFAULT 0,
    days_61_90 NUMERIC(18,4) NOT NULL DEFAULT 0,
    over_90_days NUMERIC(18,4) NOT NULL DEFAULT 0,
    total_outstanding NUMERIC(18,4) NOT NULL DEFAULT 0,
    UNIQUE(customer_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_journals_source ON financial_journals(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_account ON financial_journal_lines(account_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_customer ON financial_journal_lines(customer_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_supplier ON financial_journal_lines(supplier_id);
CREATE INDEX IF NOT EXISTS idx_payments_customer_date ON payment_transactions(customer_id, payment_date);
CREATE INDEX IF NOT EXISTS idx_payments_supplier_date ON payment_transactions(supplier_id, payment_date);
CREATE INDEX IF NOT EXISTS idx_aging_customer_date ON receivable_aging_snapshots(customer_id, snapshot_date);
