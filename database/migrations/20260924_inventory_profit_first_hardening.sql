-- E.Y.T ERP | Inventory Profit First bridge hardening
-- Operational management layer only. Inventory ledger and finalized
-- month-end inventory remain canonical sources of truth.
BEGIN;

ALTER TABLE inventory_capital_snapshots
    ADD COLUMN IF NOT EXISTS inventory_snapshot_status VARCHAR(20) NOT NULL DEFAULT 'CLOSED';

ALTER TABLE inventory_capital_snapshots
    ADD COLUMN IF NOT EXISTS sales_period_start DATE;

ALTER TABLE inventory_capital_snapshots
    ADD COLUMN IF NOT EXISTS sales_period_end DATE;

ALTER TABLE inventory_capital_snapshots
    ADD COLUMN IF NOT EXISTS sales_period_days INTEGER;

ALTER TABLE inventory_capital_snapshots
    ADD COLUMN IF NOT EXISTS valuation_method VARCHAR(40) NOT NULL DEFAULT 'MOVING_AVERAGE';

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
    s.inventory_snapshot_status,
    s.sales_period_start,
    s.sales_period_end,
    s.sales_period_days,
    s.valuation_method,
    CASE
        WHEN COALESCE(p.sales, 0) > 0
        THEN ROUND(100 * s.inventory_value / NULLIF(p.sales, 0), 2)
        ELSE 0
    END AS inventory_to_sales_pct,
    COALESCE(p.sales, 0) AS sales,
    COALESCE(p.collected_cash, 0) AS collected_cash,
    COALESCE(p.outstanding_receivable, 0) AS outstanding_receivable,
    COALESCE(p.gross_profit, 0) AS gross_profit,
    COALESCE(p.operational_cash_contribution, 0) AS operational_cash_contribution
FROM inventory_capital_snapshots s
LEFT JOIN LATERAL (
    SELECT
        SUM(sales_amount) AS sales,
        SUM(collected_cash) AS collected_cash,
        SUM(outstanding_receivable) AS outstanding_receivable,
        SUM(gross_profit) AS gross_profit,
        SUM(operational_cash_contribution) AS operational_cash_contribution
    FROM profit_first_order_control
    WHERE order_date BETWEEN s.sales_period_start AND s.sales_period_end
) p ON TRUE;

CREATE INDEX IF NOT EXISTS ix_inventory_capital_sales_period
    ON inventory_capital_snapshots(sales_period_start, sales_period_end);

COMMIT;
