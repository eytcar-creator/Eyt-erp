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

-- Finance invoice/payment tables are already canonical in the Order Center chain.
-- Do not recreate them here. The CEO dashboard consumes that schema and derives
-- due dates from customer payment terms.

CREATE OR REPLACE VIEW receivables AS
SELECT
  i.id AS invoice_id,
  so.order_no,
  i.customer_id,
  i.invoice_date,
  (i.invoice_date + COALESCE(ccp.payment_terms_days, 0))::date AS due_date,
  i.receivable_amount AS invoice_amount,
  COALESCE(pa.collected, 0) AS collected,
  GREATEST(i.receivable_amount - COALESCE(pa.collected, 0), 0) AS outstanding,
  GREATEST(0, CURRENT_DATE - (i.invoice_date + COALESCE(ccp.payment_terms_days, 0))::date) AS days_overdue
FROM invoices i
JOIN sales_orders so ON so.id = i.sales_order_id
LEFT JOIN customer_credit_profiles ccp ON ccp.customer_id = i.customer_id
LEFT JOIN (
  SELECT invoice_id, SUM(amount) AS collected
  FROM payment_allocations
  GROUP BY invoice_id
) pa ON pa.invoice_id = i.id
WHERE i.status <> 'VOID';

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
