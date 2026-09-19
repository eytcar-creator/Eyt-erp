-- EYT material consumption v1
-- Keeps the existing inventory ledger as the single stock source.
-- Adds canonical Product UUID and reservation linkage for production consumption.

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
