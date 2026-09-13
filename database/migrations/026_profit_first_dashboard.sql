-- E.Y.T ERP | Migration 026 | Profit First operational dashboard
-- Revenue, COGS, collected cash, receivables and operational cash contribution.
BEGIN;

CREATE OR REPLACE VIEW profit_first_order_control AS
SELECT
    so.id AS sales_order_id,
    so.order_no,
    so.order_date,
    so.customer_id,
    so.status AS order_status,
    COALESCE(SUM(soi.quantity * soi.unit_price),0) AS sales_amount,
    COALESCE(SUM(soi.quantity * COALESCE(NULLIF(soi.cost_snapshot,0), soi.unit_cost)),0) AS cogs_amount,
    COALESCE(SUM(soi.quantity * (soi.unit_price - COALESCE(NULLIF(soi.cost_snapshot,0), soi.unit_cost))),0) AS gross_profit,
    COALESCE(cc.collected,0) AS collected_cash,
    GREATEST(COALESCE(SUM(soi.quantity * soi.unit_price),0) - COALESCE(cc.collected,0),0) AS outstanding_receivable,
    COALESCE(cc.collected,0) - COALESCE(SUM(soi.quantity * COALESCE(NULLIF(soi.cost_snapshot,0), soi.unit_cost)),0) AS operational_cash_contribution,
    CASE WHEN COALESCE(SUM(soi.quantity * soi.unit_price),0) > 0
         THEN ROUND(100 * COALESCE(SUM(soi.quantity * (soi.unit_price - COALESCE(NULLIF(soi.cost_snapshot,0), soi.unit_cost))),0) / COALESCE(SUM(soi.quantity * soi.unit_price),0), 2)
         ELSE 0 END AS gross_margin_pct
FROM sales_orders so
JOIN sales_order_items soi ON soi.sales_order_id=so.id
LEFT JOIN (
    SELECT sales_order_id, SUM(collected) AS collected
    FROM cash_collection_control
    GROUP BY sales_order_id
) cc ON cc.sales_order_id=so.id
WHERE so.status <> 'CANCELLED'
GROUP BY so.id, so.order_no, so.order_date, so.customer_id, so.status, cc.collected;

CREATE INDEX IF NOT EXISTS ix_sales_orders_order_date ON sales_orders(order_date);

COMMIT;
