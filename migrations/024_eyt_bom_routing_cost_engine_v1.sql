-- EYT BOM + Routing + Cost Engine v1.0
-- Migration 024
-- Canonical production model on top of EYT Core Master.

CREATE TABLE IF NOT EXISTS eyt_bom (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES eyt_product_master(id),
  bom_code text NOT NULL,
  version integer NOT NULL DEFAULT 1,
  status text NOT NULL DEFAULT 'DRAFT',
  yield_factor numeric(12,6) NOT NULL DEFAULT 1,
  effective_from date,
  effective_to date,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(product_id, version),
  UNIQUE(bom_code, version)
);

CREATE TABLE IF NOT EXISTS eyt_bom_item (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bom_id uuid NOT NULL REFERENCES eyt_bom(id) ON DELETE CASCADE,
  component_product_id uuid NOT NULL REFERENCES eyt_product_master(id),
  quantity_per numeric(18,6) NOT NULL,
  scrap_percent numeric(8,4) NOT NULL DEFAULT 0,
  unit text NOT NULL DEFAULT 'PCS',
  sequence_no integer NOT NULL DEFAULT 10,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (quantity_per > 0),
  CHECK (scrap_percent >= 0 AND scrap_percent < 100),
  UNIQUE(bom_id, component_product_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS eyt_routing (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES eyt_product_master(id),
  routing_code text NOT NULL,
  version integer NOT NULL DEFAULT 1,
  status text NOT NULL DEFAULT 'DRAFT',
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(product_id, version),
  UNIQUE(routing_code, version)
);

CREATE TABLE IF NOT EXISTS eyt_routing_operation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  routing_id uuid NOT NULL REFERENCES eyt_routing(id) ON DELETE CASCADE,
  sequence_no integer NOT NULL,
  operation_code text NOT NULL,
  operation_name_fa text NOT NULL,
  operation_name_en text,
  work_center text,
  make_or_buy text NOT NULL DEFAULT 'MAKE',
  contractor_supplier_id uuid REFERENCES eyt_supplier_master(id),
  planned_days numeric(12,3) NOT NULL DEFAULT 0,
  capacity_per_day numeric(18,3) NOT NULL DEFAULT 0,
  setup_cost numeric(18,2) NOT NULL DEFAULT 0,
  unit_cost numeric(18,2) NOT NULL DEFAULT 0,
  transport_cost_per_unit numeric(18,2) NOT NULL DEFAULT 0,
  qc_required boolean NOT NULL DEFAULT false,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(routing_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS eyt_material_cost_snapshot (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES eyt_product_master(id),
  snapshot_date timestamptz NOT NULL DEFAULT now(),
  unit_cost numeric(18,2) NOT NULL,
  source text NOT NULL DEFAULT 'MASTER',
  reference_id text,
  notes text
);

CREATE TABLE IF NOT EXISTS eyt_production_cost_snapshot (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  production_order_id bigint NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
  product_id uuid REFERENCES eyt_product_master(id),
  snapshot_at timestamptz NOT NULL DEFAULT now(),
  material_cost numeric(18,2) NOT NULL DEFAULT 0,
  operation_cost numeric(18,2) NOT NULL DEFAULT 0,
  transport_cost numeric(18,2) NOT NULL DEFAULT 0,
  packaging_cost numeric(18,2) NOT NULL DEFAULT 0,
  scrap_cost numeric(18,2) NOT NULL DEFAULT 0,
  holding_cost numeric(18,2) NOT NULL DEFAULT 0,
  overhead_cost numeric(18,2) NOT NULL DEFAULT 0,
  total_cost numeric(18,2) GENERATED ALWAYS AS (
    material_cost + operation_cost + transport_cost + packaging_cost +
    scrap_cost + holding_cost + overhead_cost
  ) STORED,
  cost_per_unit numeric(18,2) NOT NULL DEFAULT 0,
  notes text
);

ALTER TABLE production_operations
  ADD COLUMN IF NOT EXISTS routing_operation_id uuid REFERENCES eyt_routing_operation(id);

ALTER TABLE material_lots
  ADD COLUMN IF NOT EXISTS component_product_id uuid REFERENCES eyt_product_master(id);

ALTER TABLE production_costs
  ADD COLUMN IF NOT EXISTS cost_source text;

CREATE INDEX IF NOT EXISTS idx_eyt_bom_product ON eyt_bom(product_id);
CREATE INDEX IF NOT EXISTS idx_eyt_bom_item_bom ON eyt_bom_item(bom_id);
CREATE INDEX IF NOT EXISTS idx_eyt_routing_product ON eyt_routing(product_id);
CREATE INDEX IF NOT EXISTS idx_eyt_routing_op_routing ON eyt_routing_operation(routing_id);
CREATE INDEX IF NOT EXISTS idx_eyt_cost_snapshot_order ON eyt_production_cost_snapshot(production_order_id);

CREATE OR REPLACE VIEW eyt_bom_cost AS
SELECT
  b.id AS bom_id,
  b.product_id,
  b.version,
  SUM(
    bi.quantity_per * (1 + bi.scrap_percent / 100.0) *
    COALESCE(pm.last_cost, pm.standard_cost, 0)
  ) AS material_cost_per_unit
FROM eyt_bom b
JOIN eyt_bom_item bi ON bi.bom_id = b.id
JOIN eyt_product_master pm ON pm.id = bi.component_product_id
GROUP BY b.id, b.product_id, b.version;

CREATE OR REPLACE VIEW eyt_routing_cost AS
SELECT
  r.id AS routing_id,
  r.product_id,
  r.version,
  SUM(ro.setup_cost + (ro.unit_cost + ro.transport_cost_per_unit)) AS operation_cost_per_unit,
  SUM(ro.planned_days) AS planned_days
FROM eyt_routing r
JOIN eyt_routing_operation ro ON ro.routing_id = r.id
GROUP BY r.id, r.product_id, r.version;

CREATE OR REPLACE VIEW eyt_product_standard_cost AS
SELECT
  p.id AS product_id,
  p.sku,
  p.product_name_fa,
  COALESCE(b.material_cost_per_unit, 0) AS bom_material_cost,
  COALESCE(r.operation_cost_per_unit, 0) AS routing_operation_cost,
  COALESCE(b.material_cost_per_unit, 0) + COALESCE(r.operation_cost_per_unit, 0)
    AS calculated_standard_cost,
  COALESCE(r.planned_days, 0) AS production_days
FROM eyt_product_master p
LEFT JOIN LATERAL (
  SELECT * FROM eyt_bom_cost x
  WHERE x.product_id = p.id
  ORDER BY x.version DESC
  LIMIT 1
) b ON true
LEFT JOIN LATERAL (
  SELECT * FROM eyt_routing_cost x
  WHERE x.product_id = p.id
  ORDER BY x.version DESC
  LIMIT 1
) r ON true;

CREATE OR REPLACE FUNCTION eyt_snapshot_production_cost(p_production_order_id bigint)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  v_product uuid;
  v_qty numeric;
  v_bom numeric := 0;
  v_ops numeric := 0;
  v_transport numeric := 0;
  v_pack numeric := 0;
  v_scrap numeric := 0;
  v_holding numeric := 0;
  v_overhead numeric := 0;
  v_id uuid;
BEGIN
  SELECT product_master_id, target_qty
    INTO v_product, v_qty
  FROM production_orders
  WHERE id = p_production_order_id;

  IF v_product IS NULL THEN
    RAISE EXCEPTION 'Production order % has no product_master_id', p_production_order_id;
  END IF;

  SELECT COALESCE(material_cost_per_unit,0) * COALESCE(v_qty,0)
    INTO v_bom
  FROM eyt_bom_cost
  WHERE product_id = v_product
  ORDER BY version DESC
  LIMIT 1;

  SELECT
    COALESCE(SUM(service_cost),0),
    COALESCE(SUM(transport_cost),0)
  INTO v_ops, v_transport
  FROM production_operations
  WHERE production_order_id = p_production_order_id;

  SELECT COALESCE(SUM(amount),0)
    INTO v_scrap
  FROM production_costs
  WHERE production_order_id = p_production_order_id
    AND cost_type = 'SCRAP';

  SELECT COALESCE(SUM(holding_cost),0)
    INTO v_holding
  FROM capital_holding_costs
  WHERE production_order_id = p_production_order_id;

  SELECT COALESCE(SUM(amount),0)
    INTO v_pack
  FROM production_costs
  WHERE production_order_id = p_production_order_id
    AND cost_type = 'PACKAGING';

  SELECT COALESCE(SUM(amount),0)
    INTO v_overhead
  FROM production_costs
  WHERE production_order_id = p_production_order_id
    AND cost_type = 'OVERHEAD';

  INSERT INTO eyt_production_cost_snapshot(
    production_order_id, product_id, material_cost, operation_cost,
    transport_cost, packaging_cost, scrap_cost, holding_cost,
    overhead_cost, cost_per_unit, notes
  )
  VALUES (
    p_production_order_id, v_product, v_bom, v_ops, v_transport,
    v_pack, v_scrap, v_holding, v_overhead,
    CASE WHEN COALESCE(v_qty,0) > 0 THEN
      (v_bom + v_ops + v_transport + v_pack + v_scrap + v_holding + v_overhead) / v_qty
    ELSE 0 END,
    'EYT Profit First production cost snapshot'
  )
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;
