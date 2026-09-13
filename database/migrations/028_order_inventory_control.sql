-- E.Y.T ERP | Migration 028 | Order Center + Inventory reservation contract
-- Compatible with the legacy warehouse/inventory schema established in migration 004.
BEGIN;

-- Migration 004 already owns warehouses. Extend it only where the later
-- contract needs a generic display name, without replacing name_fa.
ALTER TABLE warehouses
    ADD COLUMN IF NOT EXISTS name VARCHAR(200);

UPDATE warehouses
SET name = COALESCE(name, name_fa, code)
WHERE name IS NULL;

ALTER TABLE warehouses
    ALTER COLUMN name SET DEFAULT '';

INSERT INTO warehouses(code, name_fa, name_en, location, name)
VALUES ('MAIN', 'انبار اصلی E.Y.T', 'Main Warehouse', 'Main', 'انبار اصلی E.Y.T')
ON CONFLICT (code) DO UPDATE
SET name = COALESCE(warehouses.name, EXCLUDED.name);

-- Migration 004 already owns these tables. Add only missing contract fields.
ALTER TABLE inventory_transactions
    ADD COLUMN IF NOT EXISTS document_no VARCHAR(100);

ALTER TABLE inventory_reservations
    ADD COLUMN IF NOT EXISTS document_no VARCHAR(100);

ALTER TABLE inventory_reservations
    ADD COLUMN IF NOT EXISTS consumed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_inventory_tx_stock
    ON inventory_transactions(warehouse_code, product_code, created_at);
CREATE INDEX IF NOT EXISTS ix_inventory_reservation_stock
    ON inventory_reservations(warehouse_code, product_code, status);
CREATE INDEX IF NOT EXISTS ix_inventory_reservation_document
    ON inventory_reservations(document_no, product_code, status);

-- Keep the existing legacy status vocabulary valid while allowing the Order
-- Center contract's RESERVED/CONSUMED/CANCELLED states.
DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'inventory_reservations'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%status%'
    LOOP
        EXECUTE format('ALTER TABLE inventory_reservations DROP CONSTRAINT %I', r.conname);
    END LOOP;
END $$;

ALTER TABLE inventory_reservations
    ADD CONSTRAINT ck_inventory_reservations_status_eyt
    CHECK (status IN ('RESERVED','RELEASED','CONSUMED','CANCELLED'));

COMMIT;
