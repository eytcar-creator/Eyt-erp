-- E.Y.T ERP | Migration 024 | Repeat Purchase -> Sales Order Bridge
-- Adds traceability so repeat-purchase orders retain their CRM origin.
BEGIN;

ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS customer_vehicle_id UUID REFERENCES customer_vehicles(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(40),
    ADD COLUMN IF NOT EXISTS source_id UUID,
    ADD COLUMN IF NOT EXISTS source_channel VARCHAR(50);

CREATE INDEX IF NOT EXISTS ix_sales_orders_customer_vehicle
    ON sales_orders(customer_id, customer_vehicle_id, order_date);

CREATE INDEX IF NOT EXISTS ix_sales_orders_source
    ON sales_orders(source_type, source_id);

COMMIT;
