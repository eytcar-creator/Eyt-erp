-- E.Y.T ERP | Migration 011 | Order Center atomic confirmation schema
-- PostgreSQL / idempotent
BEGIN;

-- Extend the canonical sales order model used by the Order Center.
ALTER TABLE sales_orders DROP CONSTRAINT IF EXISTS sales_orders_status_check;
ALTER TABLE sales_orders ADD CONSTRAINT sales_orders_status_check
  CHECK (status IN ('DRAFT','PENDING_CONFIRMATION','CONFIRMED','RESERVED','PREPARING','READY_TO_SHIP','SHIPPED','DELIVERED','FULFILLED','CANCELLED','RETURNED'));
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS representative_id UUID REFERENCES representatives(id);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS channel VARCHAR(40);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS payment_type VARCHAR(20) NOT NULL DEFAULT 'CASH';
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(160);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_orders_idempotency_key
  ON sales_orders(idempotency_key) WHERE idempotency_key IS NOT NULL;

ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS cost_snapshot NUMERIC(18,6);
ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS contribution NUMERIC(20,6);

-- Migration 004 is the canonical reservation model. Add the later
-- document/reference fields without recreating the table.
ALTER TABLE inventory_reservations ADD COLUMN IF NOT EXISTS document_no VARCHAR(100);
ALTER TABLE inventory_reservations ALTER COLUMN document_no SET DEFAULT 'LEGACY';
UPDATE inventory_reservations SET document_no = COALESCE(document_no, reference_id, 'LEGACY-' || id::text);
ALTER TABLE inventory_reservations ALTER COLUMN document_no SET NOT NULL;
ALTER TABLE inventory_reservations DROP CONSTRAINT IF EXISTS inventory_reservations_status_check;
ALTER TABLE inventory_reservations ADD CONSTRAINT inventory_reservations_status_check
  CHECK (status IN ('RESERVED','CONSUMED','RELEASED','CANCELLED'));

-- Credit control snapshot used during atomic confirmation.
CREATE TABLE IF NOT EXISTS customer_credit_profiles (
  customer_id UUID PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
  credit_limit NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
  risk_level VARCHAR(30) NOT NULL DEFAULT 'NORMAL',
  manual_hold BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_credit_checks (
  id BIGSERIAL PRIMARY KEY,
  order_no VARCHAR(60) NOT NULL REFERENCES sales_orders(order_no) ON DELETE CASCADE,
  customer_id UUID NOT NULL REFERENCES customers(id),
  requested_amount NUMERIC(20,2) NOT NULL CHECK (requested_amount >= 0),
  allowed BOOLEAN NOT NULL,
  credit_status VARCHAR(30) NOT NULL,
  available_credit NUMERIC(20,2) NOT NULL,
  reason VARCHAR(120) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_audit_log (
  id BIGSERIAL PRIMARY KEY,
  order_no VARCHAR(60) NOT NULL REFERENCES sales_orders(order_no) ON DELETE CASCADE,
  event_type VARCHAR(80) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_order_audit_order_created ON order_audit_log(order_no, created_at);

COMMIT;
