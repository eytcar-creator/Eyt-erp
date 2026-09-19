-- EYT CI compatibility fixes.
-- This migration is intentionally additive and safe for existing environments.
ALTER TABLE price_lists
  ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS ix_price_lists_active_dates
  ON price_lists(active, valid_from, valid_to);
