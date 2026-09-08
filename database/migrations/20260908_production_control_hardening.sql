-- E.Y.T Production Control hardening
-- Append-only operational ledger for material/WIP/scrap/outsourcing/payables.
CREATE TABLE IF NOT EXISTS production_inventory_ledger (
 id BIGSERIAL PRIMARY KEY, production_order_id BIGINT REFERENCES production_orders(id), operation_id BIGINT REFERENCES production_operations(id),
 material_code VARCHAR(100), product_code VARCHAR(100), warehouse_code VARCHAR(100) NOT NULL, movement_type VARCHAR(30) NOT NULL,
 quantity NUMERIC(14,3) NOT NULL, unit VARCHAR(20) NOT NULL, reference_no VARCHAR(100), actor_name VARCHAR(255) NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, notes TEXT
);
CREATE TABLE IF NOT EXISTS production_scrap (
 id BIGSERIAL PRIMARY KEY, production_order_id BIGINT NOT NULL REFERENCES production_orders(id), operation_id BIGINT REFERENCES production_operations(id),
 product_code VARCHAR(100), quantity NUMERIC(14,3) NOT NULL CHECK(quantity>0), unit VARCHAR(20) NOT NULL, reason VARCHAR(255) NOT NULL,
 actor_name VARCHAR(255) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, notes TEXT
);
CREATE TABLE IF NOT EXISTS production_service_payables (
 id BIGSERIAL PRIMARY KEY, production_order_id BIGINT NOT NULL REFERENCES production_orders(id), operation_id BIGINT REFERENCES production_operations(id),
 contractor_name VARCHAR(255) NOT NULL, invoice_no VARCHAR(100), service_amount NUMERIC(16,2) NOT NULL DEFAULT 0,
 transport_amount NUMERIC(16,2) NOT NULL DEFAULT 0, paid_amount NUMERIC(16,2) NOT NULL DEFAULT 0,
 status VARCHAR(20) NOT NULL DEFAULT 'open', created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, paid_at TIMESTAMP, notes TEXT,
 CHECK(paid_amount>=0 AND paid_amount<=service_amount+transport_amount)
);
CREATE INDEX IF NOT EXISTS ix_production_inventory_ledger_order ON production_inventory_ledger(production_order_id,created_at);
CREATE INDEX IF NOT EXISTS ix_production_scrap_order ON production_scrap(production_order_id,created_at);
CREATE INDEX IF NOT EXISTS ix_production_service_payables_order ON production_service_payables(production_order_id,status);
