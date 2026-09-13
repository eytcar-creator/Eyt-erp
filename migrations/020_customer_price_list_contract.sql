-- E.Y.T ERP | Migration 020 | Customer Price List contract
-- Canonical customer-specific pricing used by the B2B portal and Order Center.
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS price_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE IF NOT EXISTS price_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    price_list_id UUID NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    min_quantity NUMERIC(18,3) NOT NULL DEFAULT 1 CHECK (min_quantity > 0),
    unit_price NUMERIC(18,2) NOT NULL CHECK (unit_price >= 0),
    valid_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMPTZ,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    UNIQUE(price_list_id, product_id, min_quantity, valid_from)
);

CREATE INDEX IF NOT EXISTS ix_price_lists_active_dates
    ON price_lists(active, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS ix_price_list_items_lookup
    ON price_list_items(price_list_id, product_id, active, min_quantity, valid_from);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname='fk_customers_default_price_list'
          AND conrelid='public.customers'::regclass
    ) THEN
        ALTER TABLE customers
            ADD CONSTRAINT fk_customers_default_price_list
            FOREIGN KEY (default_price_list_id) REFERENCES price_lists(id)
            ON DELETE SET NULL;
    END IF;
END $$;

COMMIT;
