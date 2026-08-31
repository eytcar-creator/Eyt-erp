-- E.Y.T ERP | Migration 009 | Unified Order Management
-- Customers + representatives + channels + pricing + reservations
-- PostgreSQL / idempotent
BEGIN;

CREATE TABLE IF NOT EXISTS sales_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(40) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sales_channels(code,name) VALUES
 ('WEBSITE','Website'),('WHATSAPP','WhatsApp'),('PHONE','Telephone'),
 ('INSTAGRAM','Instagram'),('SHOP','Physical Shop'),('REPRESENTATIVE','Representative Portal'),
 ('SALES_STAFF','Sales Staff')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS representatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    representative_code VARCHAR(60) NOT NULL UNIQUE,
    customer_id UUID UNIQUE REFERENCES customers(id),
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(80),
    territory VARCHAR(160),
    price_level VARCHAR(40) NOT NULL DEFAULT 'REPRESENTATIVE',
    credit_limit NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
    credit_balance NUMERIC(20,2) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    customer_type VARCHAR(40) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    price_list_id UUID NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    unit_price NUMERIC(18,6) NOT NULL CHECK (unit_price >= 0),
    min_quantity NUMERIC(18,6) NOT NULL DEFAULT 1 CHECK (min_quantity > 0),
    UNIQUE(price_list_id, product_id, min_quantity)
);

INSERT INTO price_lists(code,name,customer_type) VALUES
 ('RETAIL','Retail','RETAIL'),('MECHANIC','Mechanic','MECHANIC'),
 ('WHOLESALE','Wholesale','WHOLESALE'),('REPRESENTATIVE','Representative','REPRESENTATIVE'),
 ('VIP','VIP','VIP')
ON CONFLICT (code) DO NOTHING;

ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS channel_id UUID REFERENCES sales_channels(id);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS representative_id UUID REFERENCES representatives(id);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS price_list_id UUID REFERENCES price_lists(id);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS total_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS payment_status VARCHAR(30) NOT NULL DEFAULT 'UNPAID';
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS fulfillment_status VARCHAR(30) NOT NULL DEFAULT 'PENDING';

ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0);
ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS line_total NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (line_total >= 0);

CREATE TABLE IF NOT EXISTS inventory_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sales_order_id UUID NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    sales_order_item_id UUID NOT NULL REFERENCES sales_order_items(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    warehouse_code VARCHAR(60) NOT NULL REFERENCES warehouses(code),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'RESERVED',
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at TIMESTAMPTZ,
    CHECK (status IN ('RESERVED','RELEASED','FULFILLED'))
);

CREATE INDEX IF NOT EXISTS idx_representatives_territory ON representatives(territory,is_active);
CREATE INDEX IF NOT EXISTS idx_price_items_product ON price_list_items(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_channel ON sales_orders(channel_id,order_date);
CREATE INDEX IF NOT EXISTS idx_orders_rep ON sales_orders(representative_id,order_date);
CREATE INDEX IF NOT EXISTS idx_reservations_order ON inventory_reservations(sales_order_id,status);
CREATE INDEX IF NOT EXISTS idx_reservations_product_warehouse ON inventory_reservations(product_id,warehouse_code,status);

UPDATE sales_orders SET total_amount = subtotal - discount_amount WHERE total_amount = 0;

INSERT INTO eyt_permissions(code) VALUES
 ('orders.read'),('orders.write'),('orders.approve'),('orders.reserve'),('representatives.read'),('representatives.write'),('pricing.read'),('pricing.write')
ON CONFLICT (code) DO NOTHING;

INSERT INTO eyt_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM eyt_roles r CROSS JOIN eyt_permissions p
WHERE r.name='CEO' AND p.code IN ('orders.read','orders.write','orders.approve','orders.reserve','representatives.read','representatives.write','pricing.read','pricing.write')
ON CONFLICT DO NOTHING;

COMMIT;
