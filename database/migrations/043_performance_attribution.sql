-- E.Y.T ERP | Migration 042 | Performance attribution
-- Canonical production-operation performer attribution for performance control.
BEGIN;

ALTER TABLE production_operations
  ADD COLUMN IF NOT EXISTS performed_by VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_production_operations_performed_by_end
  ON production_operations(performed_by, actual_end);

COMMIT;
