-- E.Y.T ERP | Migration 020 | Customer pricing contract
-- Customer portal pricing is separate from internal users and supports
-- customer-specific price lists with a safe fallback to canonical product pricing.
BEGIN;

CREATE TABLE IF NOT EXISTS price_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    channel VARCHAR(30) NOT NULL DEFAULT 'WHOLESALE',
    currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
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
    unit_price NUMERIC(18,2) NOT NULL CHECK (unit_price > 0),
    min_quantity NUMERIC(18,6) NOT NULL DEFAULT 1 CHECK (min_quantity > 0),
    valid_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMPTZ,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    UNIQUE(price_list_id, product_id, min_quantity, valid_from)
);

ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS default_price_list_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_customers_default_price_list'
    ) THEN
        ALTER TABLE customers
            ADD CONSTRAINT fk_customers_default_price_list
            FOREIGN KEY (default_price_list_id) REFERENCES price_lists(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_price_lists_active
    ON price_lists(active, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_price_list_items_lookup
    ON price_list_items(price_list_id, product_id, active, min_quantity, valid_from);
CREATE INDEX IF NOT EXISTS idx_customers_default_price_list
    ON customers(default_price_list_id);

COMMIT;
