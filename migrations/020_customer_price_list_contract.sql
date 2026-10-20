-- Customer price-list contract
-- Ensure the price list active flag exists before indexes/constraints depend on it.
ALTER TABLE price_lists
    ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

-- Existing contract follows below.
