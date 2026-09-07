-- E.Y.T ERP | Migration 018 | Order Center schema contract
-- Canonical SQL migration path. Idempotent and PostgreSQL-compatible.
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- These columns already exist in the canonical 004 migration; IF NOT EXISTS
-- keeps this contract safe against older development databases.
ALTER TABLE products ADD COLUMN IF NOT EXISTS product_code VARCHAR(100);
ALTER TABLE products ADD COLUMN IF NOT EXISTS purchase_price NUMERIC(18,6) NOT NULL DEFAULT 0;
CREATE UNIQUE INDEX IF NOT EXISTS uq_products_product_code
    ON products(product_code) WHERE product_code IS NOT NULL;

ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS code VARCHAR(60);
CREATE UNIQUE INDEX IF NOT EXISTS uq_warehouses_code
    ON warehouses(code) WHERE code IS NOT NULL;

CREATE TABLE IF NOT EXISTS representatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    representative_code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS representative_id UUID REFERENCES representatives(id);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS channel VARCHAR(40);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS payment_type VARCHAR(40);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(200);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_orders_idempotency_key
    ON sales_orders(idempotency_key) WHERE idempotency_key IS NOT NULL;

ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS cost_snapshot NUMERIC(18,6) NOT NULL DEFAULT 0;
ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS contribution NUMERIC(18,6) NOT NULL DEFAULT 0;

ALTER TABLE inventory_reservations ADD COLUMN IF NOT EXISTS document_no VARCHAR(100);
ALTER TABLE inventory_reservations ADD COLUMN IF NOT EXISTS warehouse_code VARCHAR(100);
ALTER TABLE inventory_reservations ADD COLUMN IF NOT EXISTS product_code VARCHAR(100);
ALTER TABLE inventory_reservations ADD COLUMN IF NOT EXISTS quantity NUMERIC(18,3);
ALTER TABLE inventory_reservations ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'RESERVED';

CREATE TABLE IF NOT EXISTS customer_credit_profiles (
    customer_id UUID PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
    credit_limit NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
    payment_terms_days INTEGER NOT NULL DEFAULT 0 CHECK (payment_terms_days >= 0),
    risk_level VARCHAR(20) NOT NULL DEFAULT 'LOW',
    manual_hold BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Older Order Center migration 011 created this table without payment terms.
-- Add the field explicitly so CREATE TABLE IF NOT EXISTS remains compatible.
ALTER TABLE customer_credit_profiles
    ADD COLUMN IF NOT EXISTS payment_terms_days INTEGER NOT NULL DEFAULT 0;
ALTER TABLE customer_credit_profiles
    ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE customer_credit_profiles
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS order_credit_checks (
    id BIGSERIAL PRIMARY KEY,
    order_no VARCHAR(60) NOT NULL,
    customer_id UUID NOT NULL,
    requested_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    allowed BOOLEAN NOT NULL,
    credit_status VARCHAR(40) NOT NULL,
    available_credit NUMERIC(18,2) NOT NULL DEFAULT 0,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Migration 011 has a reason column used by the runtime adapter. Keep the
-- canonical contract compatible with both the older and newer definitions.
ALTER TABLE order_credit_checks
    ADD COLUMN IF NOT EXISTS reason VARCHAR(120);
ALTER TABLE order_credit_checks
    ADD COLUMN IF NOT EXISTS checked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS order_audit_log (
    id BIGSERIAL PRIMARY KEY,
    order_no VARCHAR(60) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    actor_id TEXT,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE order_audit_log
    ADD COLUMN IF NOT EXISTS actor_id TEXT;
ALTER TABLE order_audit_log
    ADD COLUMN IF NOT EXISTS details JSONB;

-- Canonical finance schema uses invoices.id, sales_orders.order_no and
-- payment_allocations. Build the receivables view from those real tables.
-- Due date is derived from the customer's configured payment terms because
-- the canonical invoice table does not store a separate due_date column.
DO $$
BEGIN
    IF to_regclass('public.invoices') IS NOT NULL
       AND to_regclass('public.payment_allocations') IS NOT NULL
       AND to_regclass('public.payments') IS NOT NULL THEN
        EXECUTE 'CREATE OR REPLACE VIEW receivables AS
        SELECT i.id AS invoice_id,
               so.order_no,
               i.customer_id,
               i.invoice_date,
               (i.invoice_date + COALESCE(ccp.payment_terms_days, 0))::date AS due_date,
               i.receivable_amount AS invoice_amount,
               COALESCE(pa.collected, 0) AS collected,
               GREATEST(i.receivable_amount - COALESCE(pa.collected, 0), 0) AS outstanding,
               GREATEST(0, CURRENT_DATE - (i.invoice_date + COALESCE(ccp.payment_terms_days, 0))::date) AS days_overdue
        FROM invoices i
        JOIN sales_orders so ON so.id = i.sales_order_id
        LEFT JOIN customer_credit_profiles ccp ON ccp.customer_id = i.customer_id
        LEFT JOIN (
            SELECT p.invoice_id,
                   SUM(p.amount) AS collected
            FROM payment_allocations p
            GROUP BY p.invoice_id
        ) pa ON pa.invoice_id = i.id
        WHERE i.status <> ''VOID''';
    END IF;
END $$;

COMMIT;
