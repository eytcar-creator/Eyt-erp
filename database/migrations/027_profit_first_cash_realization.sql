-- E.Y.T ERP | Migration 027 | Profit First cash-realization correction
-- Makes the Profit First view invoice-aware so receivables are based on invoiced receivables,
-- not simply order value minus collected cash.
BEGIN;

CREATE OR REPLACE VIEW profit_first_order_control AS
WITH order_lines AS (
    SELECT
        so.id AS sales_order_id,
        so.order_no,
        so.order_date,
        so.customer_id,
        so.status AS order_status,
        COALESCE(SUM(soi.quantity * soi.unit_price), 0) AS sales_amount,
        COALESCE(SUM(soi.quantity * COALESCE(NULLIF(soi.cost_snapshot, 0), soi.unit_cost)), 0) AS cogs_amount
    FROM sales_orders so
    JOIN sales_order_items soi ON soi.sales_order_id = so.id
    WHERE so.status <> 'CANCELLED'
    GROUP BY so.id, so.order_no, so.order_date, so.customer_id, so.status
),
order_cash AS (
    SELECT
        sales_order_id,
        COALESCE(SUM(collected), 0) AS collected_cash,
        COALESCE(SUM(receivable_amount), 0) AS invoiced_receivable,
        COALESCE(SUM(outstanding), 0) AS outstanding_receivable
    FROM cash_collection_control
    GROUP BY sales_order_id
)
SELECT
    ol.sales_order_id,
    ol.order_no,
    ol.order_date,
    ol.customer_id,
    ol.order_status,
    ol.sales_amount,
    ol.cogs_amount,
    ol.sales_amount - ol.cogs_amount AS gross_profit,
    COALESCE(oc.collected_cash, 0) AS collected_cash,
    COALESCE(oc.outstanding_receivable, 0) AS outstanding_receivable,
    COALESCE(oc.collected_cash, 0) - ol.cogs_amount AS operational_cash_contribution,
    CASE WHEN ol.sales_amount > 0
         THEN ROUND(100 * (ol.sales_amount - ol.cogs_amount) / ol.sales_amount, 2)
         ELSE 0 END AS gross_margin_pct,
    CASE WHEN COALESCE(oc.invoiced_receivable, 0) > 0
         THEN ROUND(100 * COALESCE(oc.collected_cash, 0) / oc.invoiced_receivable, 2)
         ELSE 0 END AS collection_realization_pct,
    COALESCE(oc.invoiced_receivable, 0) AS invoiced_receivable
FROM order_lines ol
LEFT JOIN order_cash oc ON oc.sales_order_id = ol.sales_order_id;

COMMIT;
