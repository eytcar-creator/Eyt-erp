-- EYT actual production cost v1
-- Actual material issues/returns override BOM material cost in the production snapshot.
-- Routing/other operational costs continue to come from the existing production ledger.

CREATE OR REPLACE FUNCTION eyt_snapshot_actual_production_cost(p_production_order_id bigint)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  v_product uuid;
  v_qty numeric := 0;
  v_material numeric := 0;
  v_ops numeric := 0;
  v_transport numeric := 0;
  v_pack numeric := 0;
  v_scrap numeric := 0;
  v_holding numeric := 0;
  v_overhead numeric := 0;
  v_id uuid;
BEGIN
  SELECT product_master_id, COALESCE(target_qty,0)
    INTO v_product, v_qty
  FROM production_orders
  WHERE id = p_production_order_id;

  IF v_product IS NULL THEN
    RAISE EXCEPTION 'Production order % has no product_master_id', p_production_order_id;
  END IF;

  SELECT COALESCE(SUM(
    CASE WHEN movement_type='ISSUE' THEN quantity * unit_cost
         WHEN movement_type='RETURN' THEN -quantity * unit_cost
         ELSE 0 END),0)
    INTO v_material
  FROM production_material_movements
  WHERE production_order_id = p_production_order_id;

  SELECT COALESCE(SUM(service_cost),0), COALESCE(SUM(transport_cost),0)
    INTO v_ops, v_transport
  FROM production_operations
  WHERE production_order_id = p_production_order_id;

  SELECT COALESCE(SUM(amount),0) INTO v_scrap
    FROM production_costs WHERE production_order_id=p_production_order_id AND cost_type='SCRAP';

  SELECT COALESCE(SUM(holding_cost),0) INTO v_holding
    FROM capital_holding_costs WHERE production_order_id=p_production_order_id;

  SELECT COALESCE(SUM(amount),0) INTO v_pack
    FROM production_costs WHERE production_order_id=p_production_order_id AND cost_type='PACKAGING';

  SELECT COALESCE(SUM(amount),0) INTO v_overhead
    FROM production_costs WHERE production_order_id=p_production_order_id AND cost_type='OVERHEAD';

  INSERT INTO eyt_production_cost_snapshot(
    production_order_id, product_id, material_cost, operation_cost,
    transport_cost, packaging_cost, scrap_cost, holding_cost,
    overhead_cost, cost_per_unit, notes
  )
  VALUES (
    p_production_order_id, v_product, v_material, v_ops, v_transport,
    v_pack, v_scrap, v_holding, v_overhead,
    CASE WHEN v_qty > 0 THEN
      (v_material+v_ops+v_transport+v_pack+v_scrap+v_holding+v_overhead)/v_qty
    ELSE 0 END,
    'EYT actual material consumption cost snapshot'
  )
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;

CREATE OR REPLACE VIEW eyt_production_actual_cost AS
SELECT s.*, po.order_no, po.product_code, po.product_name, po.target_qty
FROM eyt_production_cost_snapshot s
JOIN production_orders po ON po.id=s.production_order_id;
