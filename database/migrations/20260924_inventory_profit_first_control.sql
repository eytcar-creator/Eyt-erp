-- E.Y.T ERP | Inventory capital + Profit First control
-- Operational management layer. Inventory ledger remains canonical.
BEGIN;

CREATE TABLE IF NOT EXISTS inventory_capital_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    inventory_value NUMERIC(22,6) NOT NULL DEFAULT 0 CHECK (inventory_value >= 0),
    sellable_value NUMERIC(22,6) NOT NULL DEFAULT 0 CHECK (sellable_value >= 0),
    reserved_value NUMERIC(22,6) NOT NULL DEFAULT 0 CHECK (reserved_value >= 0),
    qc_hold_value NUMERIC(22,6) NOT NULL DEFAULT 0 CHECK (qc_hold_value >= 0),
    approved_variance_value NUMERIC(22,6) NOT NULL DEFAULT 0,
    days_since_prior_snapshot INTEGER,
    inventory_value_change NUMERIC(22,6) NOT NULL DEFAULT 0,
    capital_change_pct NUMERIC(18,6) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE VIEW inventory_profit_first_control AS
SELECT
    s.snapshot_date,
    s.inventory_value,
    s.sellable_value,
    s.reserved_value,
    s.qc_hold_value,
    s.approved_variance_value,
    s.inventory_value_change,
    s.capital_change_pct,
    CASE WHEN COALESCE(p.sales,0) > 0
         THEN ROUND(100*s.inventory_value/NULLIF(p.sales,0),2) ELSE 0 END AS inventory_to_sales_pct,
    COALESCE(p.sales,0) AS sales,
    COALESCE(p.collected_cash,0) AS collected_cash,
    COALESCE(p.outstanding_receivable,0) AS outstanding_receivable,
    COALESCE(p.gross_profit,0) AS gross_profit,
    COALESCE(p.operational_cash_contribution,0) AS operational_cash_contribution
FROM inventory_capital_snapshots s
LEFT JOIN LATERAL (
    SELECT
      SUM(sales_amount) AS sales,
      SUM(collected_cash) AS collected_cash,
      SUM(outstanding_receivable) AS outstanding_receivable,
      SUM(gross_profit) AS gross_profit,
      SUM(operational_cash_contribution) AS operational_cash_contribution
    FROM profit_first_order_control
    WHERE order_date BETWEEN date_trunc('month',s.snapshot_date)::date AND s.snapshot_date
) p ON TRUE;

CREATE INDEX IF NOT EXISTS ix_inventory_capital_snapshot_date
ON inventory_capital_snapshots(snapshot_date);

COMMIT;
