-- E.Y.T ERP | Migration 038 | Profitability cost fallback and order-state integrity
-- Keep profitability semantics aligned with the AI Finance missing-cost detector:
-- zero is treated as an absent snapshot, so a non-zero legacy cost may be used.
-- Draft and cancelled orders are excluded from recognized order profitability.
BEGIN;

CREATE OR REPLACE VIEW eyt_order_actual_profitability AS
SELECT
  o.order_no,
  o.customer_id,
  o.status,
  o.created_at,
  COALESCE(SUM(i.quantity*i.unit_price),0) AS sales,
  COALESCE(SUM(i.quantity*COALESCE(NULLIF(i.actual_cost_snapshot,0),NULLIF(i.cost_snapshot,0),0)),0) AS actual_cogs,
  o.sales_cost,
  o.logistics_cost,
  o.finance_cost,
  o.other_variable_cost,
  COALESCE(SUM(i.quantity*i.unit_price),0)
    - COALESCE(SUM(i.quantity*COALESCE(NULLIF(i.actual_cost_snapshot,0),NULLIF(i.cost_snapshot,0),0)),0)
    - o.sales_cost-o.logistics_cost-o.finance_cost-o.other_variable_cost AS contribution_profit,
  CASE WHEN COALESCE(SUM(i.quantity*i.unit_price),0)>0 THEN
    (
      COALESCE(SUM(i.quantity*i.unit_price),0)
      - COALESCE(SUM(i.quantity*COALESCE(NULLIF(i.actual_cost_snapshot,0),NULLIF(i.cost_snapshot,0),0)),0)
      - o.sales_cost-o.logistics_cost-o.finance_cost-o.other_variable_cost
    ) / SUM(i.quantity*i.unit_price)
  ELSE 0 END AS contribution_margin
FROM sales_orders o
LEFT JOIN sales_order_items i ON i.sales_order_id=o.id
WHERE o.status IN ('CONFIRMED','FULFILLED')
GROUP BY o.order_no,o.customer_id,o.status,o.created_at,
         o.sales_cost,o.logistics_cost,o.finance_cost,o.other_variable_cost;

CREATE OR REPLACE VIEW product_profitability_actual AS
SELECT
  i.product_id,
  COUNT(DISTINCT i.sales_order_id) AS order_count,
  COALESCE(SUM(i.quantity),0) AS units_sold,
  COALESCE(SUM(i.quantity*i.unit_price),0) AS sales,
  COALESCE(SUM(i.quantity*COALESCE(NULLIF(i.actual_cost_snapshot,0),NULLIF(i.cost_snapshot,0),0)),0) AS cogs,
  COALESCE(SUM(i.quantity*(i.unit_price-COALESCE(NULLIF(i.actual_cost_snapshot,0),NULLIF(i.cost_snapshot,0),0))),0) AS contribution_profit,
  CASE WHEN COALESCE(SUM(i.quantity*i.unit_price),0)>0 THEN
    SUM(i.quantity*(i.unit_price-COALESCE(NULLIF(i.actual_cost_snapshot,0),NULLIF(i.cost_snapshot,0),0)))
    / SUM(i.quantity*i.unit_price)
  ELSE 0 END AS contribution_margin
FROM sales_order_items i
JOIN sales_orders o ON o.id=i.sales_order_id
WHERE o.status IN ('CONFIRMED','FULFILLED')
GROUP BY i.product_id;

-- customer_profitability_actual is based on eyt_order_actual_profitability,
-- so it automatically inherits the corrected cost and order-state semantics.
COMMIT;
