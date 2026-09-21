-- EYT 2000 Ario end-to-end profit bridge hardening
-- Canonicalizes the actual-cost -> sales-order-line link used by the API.

CREATE OR REPLACE FUNCTION eyt_apply_actual_production_cost_to_order_line(
  p_order_no text,
  p_order_item_id uuid,
  p_production_order_id bigint
)
RETURNS numeric
LANGUAGE plpgsql
AS $$
DECLARE
  v_cost numeric(18,6);
  v_sales_order_id uuid;
BEGIN
  SELECT soi.sales_order_id
    INTO v_sales_order_id
  FROM sales_order_items soi
  JOIN sales_orders so ON so.id = soi.sales_order_id
  WHERE so.order_no = p_order_no
    AND soi.id = p_order_item_id;

  IF v_sales_order_id IS NULL THEN
    RAISE EXCEPTION 'Sales order item % for order % not found', p_order_item_id, p_order_no;
  END IF;

  SELECT s.cost_per_unit
    INTO v_cost
  FROM eyt_production_cost_snapshot s
  WHERE s.production_order_id = p_production_order_id
  ORDER BY s.snapshot_at DESC
  LIMIT 1;

  IF v_cost IS NULL THEN
    RAISE EXCEPTION 'No production cost snapshot exists for production order %', p_production_order_id;
  END IF;

  UPDATE sales_order_items
     SET actual_cost_snapshot = v_cost,
         cost_snapshot = v_cost,
         contribution = quantity * (unit_price - v_cost)
   WHERE id = p_order_item_id
     AND sales_order_id = v_sales_order_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Sales order item % could not be updated', p_order_item_id;
  END IF;

  RETURN v_cost;
END;
$$;
