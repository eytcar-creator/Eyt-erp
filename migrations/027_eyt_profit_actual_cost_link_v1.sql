-- EYT Profit First: actual production cost linkage.
-- Existing historical cost_snapshot values are preserved.

ALTER TABLE sales_order_items
  ADD COLUMN IF NOT EXISTS production_order_id bigint REFERENCES production_orders(id);

ALTER TABLE sales_order_items
  ADD COLUMN IF NOT EXISTS actual_cost_snapshot numeric(18,2);

CREATE INDEX IF NOT EXISTS ix_sales_order_items_production_order
  ON sales_order_items(production_order_id);

CREATE OR REPLACE FUNCTION eyt_apply_actual_production_cost_to_order_line(
  p_order_no text,
  p_order_item_id bigint,
  p_production_order_id bigint
)
RETURNS numeric
LANGUAGE plpgsql
AS $$
DECLARE
  v_unit_cost numeric(18,2);
BEGIN
  SELECT cost_per_unit INTO v_unit_cost
  FROM eyt_production_cost_snapshot
  WHERE production_order_id=p_production_order_id
  ORDER BY snapshot_at DESC
  LIMIT 1;

  IF v_unit_cost IS NULL THEN
    RAISE EXCEPTION 'No production cost snapshot for production order %', p_production_order_id;
  END IF;

  UPDATE sales_order_items
  SET production_order_id=p_production_order_id,
      actual_cost_snapshot=v_unit_cost,
      cost_snapshot=v_unit_cost,
      contribution=quantity * (unit_price-v_unit_cost)
  WHERE id=p_order_item_id
    AND order_no=p_order_no;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Order item % not found in order %', p_order_item_id, p_order_no;
  END IF;

  RETURN v_unit_cost;
END;
$$;

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
