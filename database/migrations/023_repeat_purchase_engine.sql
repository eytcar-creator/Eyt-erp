-- E.Y.T ERP | Migration 023 | Repeat Purchase Engine v1
-- Extends Migration 021 instead of redefining its reminder table.
BEGIN;

CREATE TABLE IF NOT EXISTS repeat_purchase_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    vehicle_id UUID REFERENCES vehicle_master(id) ON DELETE CASCADE,
    min_days INTEGER NOT NULL DEFAULT 30 CHECK (min_days >= 0),
    expected_days INTEGER NOT NULL DEFAULT 180 CHECK (expected_days > 0),
    max_days INTEGER NOT NULL DEFAULT 365 CHECK (max_days >= expected_days),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, vehicle_id)
);

ALTER TABLE repeat_purchase_reminders
    ADD COLUMN IF NOT EXISTS contact_channel VARCHAR(30),
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS next_order_id UUID REFERENCES sales_orders(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS ux_repeat_open_purchase
ON repeat_purchase_reminders(customer_id, customer_vehicle_id, product_id)
WHERE status='OPEN';

CREATE INDEX IF NOT EXISTS ix_repeat_due ON repeat_purchase_reminders(status, due_date);
CREATE INDEX IF NOT EXISTS ix_repeat_customer ON repeat_purchase_reminders(customer_id, due_date);

CREATE OR REPLACE VIEW repeat_purchase_opportunities AS
SELECT r.id,
       r.customer_id,
       c.customer_code,
       c.name AS customer_name,
       c.phone,
       r.customer_vehicle_id,
       r.product_id,
       p.product_code,
       p.name_fa AS product_name,
       r.due_date,
       r.status,
       r.created_at,
       GREATEST(0, CURRENT_DATE-r.due_date) AS days_overdue
FROM repeat_purchase_reminders r
JOIN customers c ON c.id=r.customer_id
JOIN products p ON p.id=r.product_id
WHERE r.status='OPEN';

COMMIT;
