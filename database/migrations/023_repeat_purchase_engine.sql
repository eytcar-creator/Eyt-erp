-- E.Y.T Repeat Purchase Engine v1
-- Derives reorder opportunities from real customer purchase history.

CREATE TABLE IF NOT EXISTS repeat_purchase_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id),
    vehicle_id UUID REFERENCES vehicle_master(id),
    min_days INTEGER NOT NULL DEFAULT 30 CHECK (min_days >= 0),
    expected_days INTEGER NOT NULL DEFAULT 180 CHECK (expected_days > 0),
    max_days INTEGER NOT NULL DEFAULT 365 CHECK (max_days >= expected_days),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, vehicle_id)
);

CREATE TABLE IF NOT EXISTS repeat_purchase_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    customer_vehicle_id UUID REFERENCES customer_vehicles(id),
    product_id UUID NOT NULL REFERENCES products(id),
    source_purchase_id UUID REFERENCES purchase_history(id),
    due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    contact_channel VARCHAR(30),
    contacted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    next_order_id UUID REFERENCES sales_orders(id),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_repeat_open_purchase
ON repeat_purchase_reminders(customer_id, customer_vehicle_id, product_id)
WHERE status='OPEN';

CREATE INDEX IF NOT EXISTS ix_repeat_due ON repeat_purchase_reminders(status, due_date);
CREATE INDEX IF NOT EXISTS ix_repeat_customer ON repeat_purchase_reminders(customer_id, due_date);

CREATE OR REPLACE VIEW repeat_purchase_opportunities AS
SELECT r.id, r.customer_id, c.customer_code, c.name customer_name, c.phone,
       r.customer_vehicle_id, r.product_id, p.product_code, p.name_fa product_name,
       r.due_date, r.status, r.created_at,
       GREATEST(0, CURRENT_DATE-r.due_date) days_overdue
FROM repeat_purchase_reminders r
JOIN customers c ON c.id=r.customer_id
JOIN products p ON p.id=r.product_id
WHERE r.status='OPEN';
