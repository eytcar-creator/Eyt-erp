-- E.Y.T ERP | Migration 005 | Purchase + Receiving v1
BEGIN;

CREATE TABLE IF NOT EXISTS purchase_orders_v1 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_no VARCHAR(60) NOT NULL UNIQUE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id),
    warehouse_code VARCHAR(60) NOT NULL REFERENCES warehouses(code),
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    total_amount NUMERIC(20,2) NOT NULL DEFAULT 0,
    prepayment_amount NUMERIC(20,2) NOT NULL DEFAULT 0,
    created_by UUID REFERENCES eyt_users(id),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('draft','approved','partially_received','received','cancelled')),
    CHECK (total_amount >= 0 AND prepayment_amount >= 0 AND prepayment_amount <= total_amount)
);

CREATE TABLE IF NOT EXISTS purchase_order_items_v1 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders_v1(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(18,6) NOT NULL CHECK (unit_price >= 0),
    UNIQUE(purchase_order_id, product_id)
);

CREATE TABLE IF NOT EXISTS purchase_receipts_v1 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_no VARCHAR(60) NOT NULL UNIQUE,
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders_v1(id),
    warehouse_code VARCHAR(60) NOT NULL REFERENCES warehouses(code),
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    received_by UUID REFERENCES eyt_users(id),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS purchase_receipt_items_v1 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id UUID NOT NULL REFERENCES purchase_receipts_v1(id) ON DELETE CASCADE,
    purchase_order_item_id UUID NOT NULL REFERENCES purchase_order_items_v1(id),
    product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    unit_cost NUMERIC(18,6) NOT NULL CHECK (unit_cost >= 0),
    UNIQUE(receipt_id, purchase_order_item_id)
);

CREATE INDEX IF NOT EXISTS idx_po_v1_supplier ON purchase_orders_v1(supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_po_item_v1_product ON purchase_order_items_v1(product_id);
CREATE INDEX IF NOT EXISTS idx_receipt_v1_po ON purchase_receipts_v1(purchase_order_id, received_at);
CREATE INDEX IF NOT EXISTS idx_receipt_item_v1_product ON purchase_receipt_items_v1(product_id);

INSERT INTO eyt_permissions(code) VALUES ('procurement.write'),('procurement.receive') ON CONFLICT (code) DO NOTHING;
INSERT INTO eyt_role_permissions(role_id, permission_id)
SELECT r.id,p.id FROM eyt_roles r CROSS JOIN eyt_permissions p
WHERE r.name='CEO' AND p.code IN ('procurement.write','procurement.receive')
ON CONFLICT DO NOTHING;

COMMIT;
