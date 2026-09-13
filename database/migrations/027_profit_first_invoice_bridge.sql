-- E.Y.T ERP | Migration 027 | Profit First invoice bridge
-- Preserve the existing 026 view column order while appending invoice-aware fields.
BEGIN;

CREATE OR REPLACE VIEW profit_first_order_control AS
SELECT
    so.id AS sales_order_id,
    so.order_no,
    so.order_date,
    so.customer_id,
    so.status AS order_status,
    COALESCE(SUM(soi.quantity * soi.unit_price), 0) AS sales_amount,
    COALESCE(SUM(soi.quantity * COALESCE(NULLIF(soi.cost_snapshot, 0), soi.unit_cost)), 0) AS cogs_amount,
    COALESCE(SUM(soi.quantity * (soi.unit_price - COALESCE(NULLIF(soi.cost_snapshot, 0), soi.unit_cost))), 0) AS gross_profit,
    COALESCE(MAX(ic.collected), 0) AS collected_cash,
    GREATEST(COALESCE(MAX(ic.invoiced_receivable), 0) - COALESCE(MAX(ic.collected), 0), 0) AS outstanding_receivable,
    COALESCE(MAX(ic.collected), 0)
      - COALESCE(SUM(soi.quantity * COALESCE(NULLIF(soi.cost_snapshot, 0), soi.unit_cost)), 0) AS operational_cash_contribution,
    CASE
        WHEN COALESCE(SUM(soi.quantity * soi.unit_price), 0) > 0
        THEN ROUND(100 * COALESCE(SUM(soi.quantity * (soi.unit_price - COALESCE(NULLIF(soi.cost_snapshot, 0), soi.unit_cost))), 0)
             / SUM(soi.quantity * soi.unit_price), 2)
        ELSE 0
    END AS gross_margin_pct,
    COALESCE(MAX(ic.invoiced_receivable), 0) AS invoiced_receivable,
    CASE
        WHEN COALESCE(MAX(ic.invoiced_receivable), 0) > 0
        THEN ROUND(100 * COALESCE(MAX(ic.collected), 0) / MAX(ic.invoiced_receivable), 2)
        ELSE 0
    END AS collection_realization_pct
FROM sales_orders so
JOIN sales_order_items soi ON soi.sales_order_id = so.id
LEFT JOIN (
    SELECT
        sales_order_id,
        SUM(receivable_amount) AS invoiced_receivable,
        SUM(collected) AS collected
    FROM cash_collection_control
    GROUP BY sales_order_id
) ic ON ic.sales_order_id = so.id
WHERE so.status <> 'CANCELLED'
GROUP BY so.id, so.order_no, so.order_date, so.customer_id, so.status;

COMMIT;
