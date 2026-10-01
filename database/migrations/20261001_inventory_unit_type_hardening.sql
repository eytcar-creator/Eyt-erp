-- E.Y.T ERP: normalize legacy inventory unit contract
-- The canonical inventory ledger uses a text unit such as PCS.
-- Some legacy databases may have created inventory_transactions.unit with
-- a numeric type before the canonical migration. Normalize it in-place.
ALTER TABLE inventory_transactions
    ALTER COLUMN unit TYPE VARCHAR(20)
    USING unit::text;

ALTER TABLE inventory_transactions
    ALTER COLUMN unit SET DEFAULT 'PCS';
