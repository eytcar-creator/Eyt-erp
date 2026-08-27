-- E.Y.T ERP | Phase 6 Sales, CRM & Order-to-Cash
-- PostgreSQL

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_code VARCHAR(50) NOT NULL UNIQUE,
    name_fa VARCHAR(250) NOT NULL,
    customer_type VARCHAR(30) NOT NULL DEFAULT 'WHOLESALE'
        CHECK (customer_type IN ('WHOLESALE','RETAIL','DISTRIBUTOR','DEALER','GARAGE','ONLINE','OTHER')),
    phone VARCHAR(50),
    tax_id VARCHAR(100),
    credit_limit NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
    payment_terms_days INTEGER NOT NULL DEFAULT 0 CHECK (payment_terms_days >= 0),
    minimum_margin_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (minimum_margin_percent >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customer_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name_fa VARCHAR(200) NOT NULL,
    role VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(200),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS sales_quotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quotation_no VARCHAR(80) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    quotation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until DATE,
    status VARCHAR(25) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','SENT','ACCEPTED','REJECTED','EXPIRED','CANCELLED')),
    subtotal NUMERIC(18,4) NOT NULL DEFAULT 0,
    discount_total NUMERIC(18,4) NOT NULL DEFAULT 0,
    tax_total NUMERIC(18,4) NOT NULL DEFAULT 0,
    total_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
    created_by UUID,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS sales_quotation_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quotation_id UUID NOT NULL REFERENCES sales_quotations(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(18,4) NOT NULL CHECK (unit_price >= 0),
    discount_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (discount_percent BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS sales_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_no VARCHAR(80) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    quotation_id UUID REFERENCES sales_quotations(id),
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    requested_delivery_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','PENDING_APPROVAL','APPROVED','CREDIT_HOLD','STOCK_HOLD','CONFIRMED','PARTIALLY_DELIVERED','DELIVERED','INVOICED','CANCELLED','CLOSED')),
    subtotal NUMERIC(18,4) NOT NULL DEFAULT 0,
    discount_total NUMERIC(18,4) NOT NULL DEFAULT 0,
    tax_total NUMERIC(18,4) NOT NULL DEFAULT 0,
    total_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
    created_by UUID,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS sales_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sales_order_id UUID NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    ordered_quantity NUMERIC(18,6) NOT NULL CHECK (ordered_quantity > 0),
    reserved_quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
    delivered_quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
    invoiced_quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
    unit_price NUMERIC(18,4) NOT NULL CHECK (unit_price >= 0),
    discount_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (discount_percent BETWEEN 0 AND 100),
    minimum_margin_override BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_no VARCHAR(80) NOT NULL UNIQUE,
    sales_order_id UUID NOT NULL REFERENCES sales_orders(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    delivery_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    status VARCHAR(25) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','PICKING','READY','SHIPPED','DELIVERED','CANCELLED')),
    delivered_by UUID,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS delivery_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id UUID NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
    sales_order_item_id UUID NOT NULL REFERENCES sales_order_items(id),
    product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    lot_id UUID REFERENCES inventory_lots(id)
);

CREATE TABLE IF NOT EXISTS sales_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_no VARCHAR(80) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    sales_order_id UUID REFERENCES sales_orders(id),
    invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE,
    status VARCHAR(25) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','ISSUED','PARTIALLY_PAID','PAID','OVERDUE','CANCELLED')),
    subtotal NUMERIC(18,4) NOT NULL DEFAULT 0,
    discount_total NUMERIC(18,4) NOT NULL DEFAULT 0,
    tax_total NUMERIC(18,4) NOT NULL DEFAULT 0,
    total_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
    paid_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
    balance_due NUMERIC(18,4) NOT NULL DEFAULT 0,
    created_by UUID,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS sales_invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES sales_invoices(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(18,4) NOT NULL CHECK (unit_price >= 0),
    discount_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (discount_percent BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS customer_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_no VARCHAR(80) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    invoice_id UUID REFERENCES sales_invoices(id),
    receipt_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    amount NUMERIC(18,4) NOT NULL CHECK (amount > 0),
    payment_method VARCHAR(30) NOT NULL CHECK (payment_method IN ('BANK_TRANSFER','CASH','CARD','CHEQUE','OTHER')),
    reference_no VARCHAR(120),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','CONFIRMED','REJECTED','REVERSED')),
    received_by UUID,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_customers_active ON customers(is_active, customer_type);
CREATE INDEX IF NOT EXISTS idx_sales_orders_customer_status ON sales_orders(customer_id, status);
CREATE INDEX IF NOT EXISTS idx_sales_orders_delivery_date ON sales_orders(requested_delivery_date, status);
CREATE INDEX IF NOT EXISTS idx_sales_order_items_product ON sales_order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_customer_status ON deliveries(customer_id, status);
CREATE INDEX IF NOT EXISTS idx_invoices_customer_status_due ON sales_invoices(customer_id, status, due_date);
CREATE INDEX IF NOT EXISTS idx_receipts_customer_date ON customer_receipts(customer_id, receipt_date);
