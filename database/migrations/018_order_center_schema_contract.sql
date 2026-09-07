-- E.Y.T ERP | Migration 018 | Order Center schema contract
-- Canonical SQL migration path. Idempotent and PostgreSQL-compatible.
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

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

ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS representative_id UUID;
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
    customer_id UUID PRIMARY KEY,
    credit_limit NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
    payment_terms_days INTEGER NOT NULL DEFAULT 0 CHECK (payment_terms_days >= 0),
    risk_level VARCHAR(20) NOT NULL DEFAULT 'LOW',
    manual_hold BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS order_audit_log (
    id BIGSERIAL PRIMARY KEY,
    order_no VARCHAR(60) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    actor_id TEXT,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Compatibility view: financial SQL migrations define receivables as a view.
-- Ensure the required columns are exposed by the canonical financial view.
DO $$
BEGIN
    IF to_regclass('public.invoices') IS NOT NULL THEN
        EXECUTE 'CREATE OR REPLACE VIEW receivables AS
        SELECT i.invoice_id, i.order_no, i.customer_id, i.invoice_date, i.due_date,
               i.net_amount AS invoice_amount,
               COALESCE(SUM(CASE WHEN p.status = ''POSTED'' THEN p.amount ELSE 0 END),0) AS collected,
               i.net_amount - COALESCE(SUM(CASE WHEN p.status = ''POSTED'' THEN p.amount ELSE 0 END),0) AS outstanding,
               GREATEST(0, CURRENT_DATE - i.due_date) AS days_overdue
        FROM invoices i
        LEFT JOIN payments p ON p.invoice_id = i.invoice_id
        WHERE i.status <> ''VOID''
        GROUP BY i.invoice_id';
    END IF;
END $$;

COMMIT;
