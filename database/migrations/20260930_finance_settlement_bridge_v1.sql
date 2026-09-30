ALTER TABLE payments ADD COLUMN IF NOT EXISTS funding_source_id BIGINT REFERENCES finance_funding_sources(id);
ALTER TABLE production_payments ADD COLUMN IF NOT EXISTS funding_source_id BIGINT REFERENCES finance_funding_sources(id);
CREATE INDEX IF NOT EXISTS idx_payments_funding_source ON payments(funding_source_id);
CREATE INDEX IF NOT EXISTS idx_production_payments_funding_source ON production_payments(funding_source_id);