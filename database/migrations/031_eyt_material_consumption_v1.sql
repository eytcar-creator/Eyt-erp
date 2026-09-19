-- EYT material consumption v1
-- Legacy-safe canonical base for production material movements.
CREATE TABLE IF NOT EXISTS production_material_movements (
  id BIGSERIAL PRIMARY KEY,
  production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
  operation_id BIGINT REFERENCES production_operations(id),
  material_code VARCHAR(100) NOT NULL,
  warehouse_code VARCHAR(100) NOT NULL,
  quantity NUMERIC(14,3) NOT NULL CHECK(quantity>0),
  movement_type VARCHAR(20) NOT NULL CHECK(movement_type IN ('ISSUE','RETURN')),
  document_no VARCHAR(100) NOT NULL,
  actor_name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  notes TEXT
);
CREATE INDEX IF NOT EXISTS ix_production_material_movements_order
  ON production_material_movements(production_order_id,created_at);

ALTER TABLE production_material_movements
  ADD COLUMN IF NOT EXISTS component_product_id uuid REFERENCES eyt_product_master(id);

ALTER TABLE production_material_movements
  ADD COLUMN IF NOT EXISTS reservation_id bigint REFERENCES inventory_reservations(id);

ALTER TABLE production_material_movements
  ADD COLUMN IF NOT EXISTS unit_cost numeric(18,6) NOT NULL DEFAULT 0;

ALTER TABLE production_material_movements
  ADD COLUMN IF NOT EXISTS quantity_source text NOT NULL DEFAULT 'ACTUAL';

CREATE INDEX IF NOT EXISTS ix_production_material_movements_product
  ON production_material_movements(component_product_id, production_order_id);

CREATE INDEX IF NOT EXISTS ix_production_material_movements_reservation
  ON production_material_movements(reservation_id);

COMMENT ON COLUMN production_material_movements.quantity_source
  IS 'STANDARD_BOM for planned requirement, ACTUAL for posted issue/return.';
