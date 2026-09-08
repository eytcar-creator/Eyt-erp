-- E.Y.T production inventory/WIP hardening
-- Uses the canonical inventory_transactions ledger; no parallel stock balance.
CREATE TABLE IF NOT EXISTS production_wip_transfers (
 id BIGSERIAL PRIMARY KEY,
 production_order_id BIGINT NOT NULL REFERENCES production_orders(id),
 from_operation_id BIGINT REFERENCES production_operations(id),
 to_operation_id BIGINT REFERENCES production_operations(id),
 product_code VARCHAR(100) NOT NULL,
 warehouse_code VARCHAR(100) NOT NULL,
 quantity NUMERIC(14,3) NOT NULL CHECK(quantity>0),
 document_no VARCHAR(100) NOT NULL UNIQUE,
 status VARCHAR(20) NOT NULL DEFAULT 'posted',
 actor_name VARCHAR(255) NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 notes TEXT
);
CREATE INDEX IF NOT EXISTS ix_production_wip_order ON production_wip_transfers(production_order_id,created_at);

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
CREATE INDEX IF NOT EXISTS ix_production_material_movements_order ON production_material_movements(production_order_id,created_at);
