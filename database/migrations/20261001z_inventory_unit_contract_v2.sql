-- E.Y.T ERP | Inventory transaction unit contract hardening v2
-- Canonical contract: inventory_transactions.unit is textual (PCS, KG, SET, ...)
-- This migration is intentionally placed after all legacy inventory migrations.

BEGIN;

ALTER TABLE inventory_transactions
    ALTER COLUMN unit DROP DEFAULT;

ALTER TABLE inventory_transactions
    ALTER COLUMN unit TYPE VARCHAR(20)
    USING unit::text;

ALTER TABLE inventory_transactions
    ALTER COLUMN unit SET DEFAULT 'PCS';

DO $$
DECLARE
    v_type text;
BEGIN
    SELECT format_type(a.atttypid, a.atttypmod)
      INTO v_type
      FROM pg_attribute a
     WHERE a.attrelid = 'inventory_transactions'::regclass
       AND a.attname = 'unit'
       AND NOT a.attisdropped;

    IF v_type <> 'character varying(20)' THEN
        RAISE EXCEPTION 'inventory_transactions.unit contract invalid: %', v_type;
    END IF;
END $$;

COMMIT;
