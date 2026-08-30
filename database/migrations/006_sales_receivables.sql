-- E.Y.T ERP | Migration 006 | Sales + Invoicing + Receivables
-- PostgreSQL / idempotent
BEGIN;

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(80),
    tax_id VARCHAR(80),
    address TEXT,
    credit_limit NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_no VARCHAR(60) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    warehouse_code VARCHAR(60) NOT NULL REFERENCES warehouses(code),
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
    subtotal NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    prepayment_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (prepayment_amount >= 0),
    created_by UUID REFERENCES eyt_users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (prepayment_amount <= subtotal),
    CHECK (status IN ('DRAFT','CONFIRMED','FULFILLED','CANCELLED'))
);

CREATE TABLE IF NOT EXISTS sales_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sales_order_id UUID NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(18,6) NOT NULL CHECK (unit_price >= 0),
    unit_cost NUMERIC(18,6) NOT NULL CHECK (unit_cost >= 0),
    UNIQUE(sales_order_id, product_id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_no VARCHAR(60) NOT NULL UNIQUE,
    sales_order_id UUID NOT NULL UNIQUE REFERENCES sales_orders(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
    subtotal NUMERIC(20,2) NOT NULL CHECK (subtotal >= 0),
    prepayment_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (prepayment_amount >= 0),
    receivable_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (receivable_amount >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'ISSUED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (prepayment_amount <= subtotal),
    CHECK (receivable_amount = subtotal - prepayment_amount),
    CHECK (status IN ('ISSUED','PARTIALLY_PAID','PAID','VOID'))
);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    amount NUMERIC(20,2) NOT NULL CHECK (amount > 0),
    payment_method VARCHAR(40),
    reference_no VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    amount NUMERIC(20,2) NOT NULL CHECK (amount > 0),
    UNIQUE(payment_id, invoice_id)
);

CREATE INDEX IF NOT EXISTS idx_sales_orders_customer_status ON sales_orders(customer_id,status,order_date);
CREATE INDEX IF NOT EXISTS idx_sales_items_product ON sales_order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_invoices_customer_status ON invoices(customer_id,status,invoice_date);
CREATE INDEX IF NOT EXISTS idx_payments_customer_date ON payments(customer_id,payment_date);
CREATE INDEX IF NOT EXISTS idx_payment_alloc_invoice ON payment_allocations(invoice_id);

INSERT INTO eyt_permissions(code) VALUES
 ('sales.write'),('sales.read'),('sales.fulfill'),('finance.write')
ON CONFLICT (code) DO NOTHING;
INSERT INTO eyt_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM eyt_roles r CROSS JOIN eyt_permissions p
WHERE r.name='CEO' AND p.code IN ('sales.write','sales.read','sales.fulfill','finance.write')
ON CONFLICT DO NOTHING;

COMMIT;
