-- E.Y.T Cost Snapshot
-- Immutable order-line cost snapshot foundation for Profit First.

ALTER TABLE sales_order_items
  ADD COLUMN IF NOT EXISTS cost_snapshot NUMERIC(18,2);

ALTER TABLE sales_order_items
  ADD COLUMN IF NOT EXISTS contribution NUMERIC(18,2);

CREATE OR REPLACE FUNCTION snapshot_order_line_costs(p_order_no TEXT)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_count INTEGER;
BEGIN
  UPDATE sales_order_items i
  SET cost_snapshot = COALESCE(i.cost_snapshot, p.standard_cost, 0),
      contribution = i.quantity * (i.unit_price - COALESCE(i.cost_snapshot, p.standard_cost, 0))
  FROM products p
  WHERE i.order_no = p_order_no
    AND i.product_id = p.product_uuid
    AND i.cost_snapshot IS NULL;

  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_sales_order_items_cost_snapshot
  ON sales_order_items(order_no, cost_snapshot);
