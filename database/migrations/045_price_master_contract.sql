-- E.Y.T ERP | Migration 045 | Canonical price master
-- Versioned fallback price source used by Order Center and E.Y.T One.
BEGIN;

CREATE TABLE IF NOT EXISTS price_master (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  final_price NUMERIC(18,2) NOT NULL CHECK (final_price >= 0),
  status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
  effective_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  effective_to TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (effective_to IS NULL OR effective_to > effective_from)
);

CREATE INDEX IF NOT EXISTS ix_price_master_product_effective
  ON price_master(product_id, status, effective_from DESC, effective_to);

COMMIT;
