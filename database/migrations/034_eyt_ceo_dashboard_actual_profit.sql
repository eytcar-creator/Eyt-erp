-- Canonical finance prerequisites required by the CEO cash dashboard.
CREATE TABLE IF NOT EXISTS cash_accounts (
  account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_name TEXT NOT NULL UNIQUE,
  account_type TEXT NOT NULL CHECK (account_type IN ('BANK','CASH','CARD','OTHER')),
  opening_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','INACTIVE')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cash_transactions (
  cash_transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES cash_accounts(account_id),
  transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
  type TEXT NOT NULL CHECK (type IN ('INFLOW','OUTFLOW')),
  category TEXT NOT NULL,
  amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
  reference_type TEXT,
  reference_id TEXT,
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoices (
  invoice_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_no TEXT NULL REFERENCES sales_orders(order_no),
  customer_id UUID NOT NULL,
  invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
  due_date DATE NOT NULL,
  gross_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (gross_amount >= 0),
  discount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (discount >= 0),
  net_amount NUMERIC(18,2) GENERATED ALWAYS AS (gross_amount - discount) STORED,
  status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('DRAFT','OPEN','PARTIALLY_PAID','PAID','VOID')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (discount <= gross_amount)
);

CREATE TABLE IF NOT EXISTS payments (
  payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id UUID NOT NULL REFERENCES invoices(invoice_id),
  customer_id UUID NOT NULL,
  payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
  amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
  payment_method TEXT NOT NULL CHECK (payment_method IN ('CASH','BANK_TRANSFER','CARD','CHEQUE','OTHER')),
  reference TEXT,
  idempotency_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'POSTED' CHECK (status IN ('PENDING','POSTED','REVERSED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS financial_audit_log (
  id BIGSERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  before_state JSONB,
  after_state JSONB,
  reason TEXT,
  actor_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_cash_transactions_date ON cash_transactions(transaction_date);

CREATE OR REPLACE VIEW receivables AS
SELECT i.invoice_id, i.order_no, i.customer_id, i.invoice_date, i.due_date,
       i.net_amount AS invoice_amount,
       COALESCE(SUM(CASE WHEN p.status='POSTED' THEN p.amount ELSE 0 END),0) AS collected,
       i.net_amount - COALESCE(SUM(CASE WHEN p.status='POSTED' THEN p.amount ELSE 0 END),0) AS outstanding,
       GREATEST(0, CURRENT_DATE - i.due_date) AS days_overdue
FROM invoices i LEFT JOIN payments p ON p.invoice_id=i.invoice_id
WHERE i.status <> 'VOID'
GROUP BY i.invoice_id;

-- E.Y.T CEO Dashboard: cash, receivables, inventory and contribution profit

CREATE OR REPLACE VIEW ceo_cash_position AS
SELECT
  COALESCE(SUM(CASE WHEN type='INFLOW' THEN amount ELSE 0 END),0) AS total_inflow,
  COALESCE(SUM(CASE WHEN type='OUTFLOW' THEN amount ELSE 0 END),0) AS total_outflow,
  COALESCE(SUM(CASE WHEN type='INFLOW' THEN amount ELSE -amount END),0) AS net_cash_movement
FROM cash_transactions;

CREATE OR REPLACE VIEW ceo_receivables AS
SELECT
  COALESCE(SUM(outstanding),0) AS outstanding_receivables,
  COALESCE(SUM(CASE WHEN days_overdue > 0 THEN outstanding ELSE 0 END),0) AS overdue_receivables,
  COALESCE(SUM(CASE WHEN days_overdue >= 60 THEN outstanding ELSE 0 END),0) AS high_risk_receivables
FROM receivables;

CREATE OR REPLACE VIEW ceo_profit AS
SELECT
  COALESCE(SUM(net_sales),0) AS net_sales,
  COALESCE(SUM(contribution_profit),0) AS contribution_profit,
  CASE WHEN COALESCE(SUM(net_sales),0) > 0
       THEN SUM(contribution_profit) / SUM(net_sales) ELSE 0 END AS contribution_margin
FROM eyt_order_actual_profitability;

CREATE OR REPLACE VIEW ceo_dashboard AS
SELECT
  c.net_cash_movement,
  r.outstanding_receivables,
  r.overdue_receivables,
  r.high_risk_receivables,
  p.net_sales,
  p.contribution_profit,
  p.contribution_margin,
  COALESCE((SELECT SUM(cpa.contribution_profit) FROM customer_profitability_actual cpa),0) AS actual_customer_contribution_profit,
  COALESCE((SELECT SUM(ppa.contribution_profit) FROM product_profitability_actual ppa),0) AS actual_product_contribution_profit,
  COALESCE((SELECT COUNT(*) FROM product_profitability_actual),0) AS profitable_product_rows,
  COALESCE((SELECT COUNT(*) FROM customer_profitability_actual),0) AS profitable_customer_rows,
  NOW() AS generated_at
FROM ceo_cash_position c
CROSS JOIN ceo_receivables r
CROSS JOIN ceo_profit p;
