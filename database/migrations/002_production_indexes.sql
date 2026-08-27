-- Additional production indexes for API workloads
CREATE INDEX IF NOT EXISTS idx_production_orders_status ON production_orders(status);
CREATE INDEX IF NOT EXISTS idx_production_orders_product ON production_orders(product_code);
CREATE INDEX IF NOT EXISTS idx_production_operations_status ON production_operations(status);
CREATE INDEX IF NOT EXISTS idx_production_operations_contractor ON production_operations(contractor_name);
CREATE INDEX IF NOT EXISTS idx_production_costs_type ON production_costs(production_order_id, cost_type);
CREATE INDEX IF NOT EXISTS idx_collections_status_due ON collections(status, due_date);
CREATE INDEX IF NOT EXISTS idx_traceability_order_time ON production_traceability(production_order_id, event_time);
