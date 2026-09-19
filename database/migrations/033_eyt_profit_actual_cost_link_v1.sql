CREATE OR REPLACE VIEW eyt_order_actual_profitability AS
SELECT
  o.order_no,
  o.customer_id,
  o.status,
  o.created_at,
  COALESCE(SUM(i.quantity*i.unit_price),0) AS sales,
  COALESCE(SUM(i.quantity*COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)),0) AS actual_cogs,
  o.sales_cost,
  o.logistics_cost,
  o.finance_cost,
  o.other_variable_cost,
  COALESCE(SUM(i.quantity*i.unit_price),0)
    - COALESCE(SUM(i.quantity*COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)),0)
    - o.sales_cost-o.logistics_cost-o.finance_cost-o.other_variable_cost AS contribution_profit,
  CASE WHEN COALESCE(SUM(i.quantity*i.unit_price),0)>0 THEN
    (
      COALESCE(SUM(i.quantity*i.unit_price),0)
      - COALESCE(SUM(i.quantity*COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)),0)
      - o.sales_cost-o.logistics_cost-o.finance_cost-o.other_variable_cost
    ) / SUM(i.quantity*i.unit_price)
  ELSE 0 END AS contribution_margin
FROM sales_orders o
LEFT JOIN sales_order_items i ON i.order_no=o.order_no
GROUP BY o.order_no,o.customer_id,o.status,o.created_at,
         o.sales_cost,o.logistics_cost,o.finance_cost,o.other_variable_cost;

CREATE OR REPLACE VIEW product_profitability_actual AS
SELECT
  i.product_id,
  COUNT(DISTINCT i.order_no) AS order_count,
  COALESCE(SUM(i.quantity),0) AS units_sold,
  COALESCE(SUM(i.quantity*i.unit_price),0) AS sales,
  COALESCE(SUM(i.quantity*COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)),0) AS cogs,
  COALESCE(SUM(i.quantity*(i.unit_price-COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0))),0) AS contribution_profit,
  CASE WHEN COALESCE(SUM(i.quantity*i.unit_price),0)>0 THEN
    SUM(i.quantity*(i.unit_price-COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)))
    / SUM(i.quantity*i.unit_price)
  ELSE 0 END AS contribution_margin
FROM sales_order_items i
GROUP BY i.product_id;


CREATE OR REPLACE VIEW customer_profitability_actual AS
SELECT
  o.customer_id,
  COUNT(*) AS order_count,
  COALESCE(SUM(o.sales),0) AS net_sales,
  COALESCE(SUM(o.contribution_profit),0) AS contribution_profit,
  CASE WHEN COALESCE(SUM(o.sales),0)>0
       THEN SUM(o.contribution_profit)/SUM(o.sales) ELSE 0 END AS contribution_margin
FROM eyt_order_actual_profitability o
GROUP BY o.customer_id;

