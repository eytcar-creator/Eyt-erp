-- E.Y.T Profit First: contribution profit engine
-- Uses immutable line cost snapshots so historical orders remain stable.

ALTER TABLE sales_orders
  ADD COLUMN IF NOT EXISTS sales_cost NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (sales_cost >= 0);
ALTER TABLE sales_orders
  ADD COLUMN IF NOT EXISTS logistics_cost NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (logistics_cost >= 0);
ALTER TABLE sales_orders
  ADD COLUMN IF NOT EXISTS finance_cost NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (finance_cost >= 0);
ALTER TABLE sales_orders
  ADD COLUMN IF NOT EXISTS other_variable_cost NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (other_variable_cost >= 0);

CREATE OR REPLACE VIEW order_profitability AS
SELECT
  o.order_no,
  o.customer_id,
  o.status,
  o.created_at,
  COALESCE(SUM(i.quantity * i.unit_price),0) AS gross_sales,
  COALESCE(SUM(i.quantity * i.unit_price),0) AS net_sales,
  COALESCE(SUM(i.quantity * COALESCE(i.cost_snapshot,0)),0) AS cogs,
  o.sales_cost,
  o.logistics_cost,
  o.finance_cost,
  o.other_variable_cost,
  COALESCE(SUM(i.quantity * i.unit_price),0)
    - COALESCE(SUM(i.quantity * COALESCE(i.cost_snapshot,0)),0)
    - o.sales_cost
    - o.logistics_cost
    - o.finance_cost
    - o.other_variable_cost AS contribution_profit,
  CASE
    WHEN COALESCE(SUM(i.quantity * i.unit_price),0) > 0 THEN
      (
        COALESCE(SUM(i.quantity * i.unit_price),0)
        - COALESCE(SUM(i.quantity * COALESCE(i.cost_snapshot,0)),0)
        - o.sales_cost - o.logistics_cost - o.finance_cost - o.other_variable_cost
      ) / SUM(i.quantity * i.unit_price)
    ELSE 0
  END AS contribution_margin
FROM sales_orders o
LEFT JOIN sales_order_items i ON i.order_no = o.order_no
GROUP BY o.order_no, o.customer_id, o.status, o.created_at,
         o.sales_cost, o.logistics_cost, o.finance_cost, o.other_variable_cost;

CREATE OR REPLACE VIEW customer_profitability AS
SELECT
  customer_id,
  COUNT(*) AS order_count,
  COALESCE(SUM(net_sales),0) AS net_sales,
  COALESCE(SUM(contribution_profit),0) AS contribution_profit,
  CASE WHEN COALESCE(SUM(net_sales),0) > 0
       THEN SUM(contribution_profit) / SUM(net_sales)
       ELSE 0 END AS contribution_margin
FROM order_profitability
GROUP BY customer_id;

CREATE OR REPLACE VIEW product_profitability AS
SELECT
  i.product_id,
  COUNT(DISTINCT i.order_no) AS order_count,
  COALESCE(SUM(i.quantity),0) AS units_sold,
  COALESCE(SUM(i.quantity * i.unit_price),0) AS sales,
  COALESCE(SUM(i.quantity * COALESCE(i.cost_snapshot,0)),0) AS cogs,
  COALESCE(SUM(i.quantity * (i.unit_price - COALESCE(i.cost_snapshot,0))),0) AS contribution_profit,
  CASE WHEN COALESCE(SUM(i.quantity * i.unit_price),0) > 0
       THEN SUM(i.quantity * (i.unit_price - COALESCE(i.cost_snapshot,0)))
            / SUM(i.quantity * i.unit_price)
       ELSE 0 END AS contribution_margin
FROM sales_order_items i
GROUP BY i.product_id;
