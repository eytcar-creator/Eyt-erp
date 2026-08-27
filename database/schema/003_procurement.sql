-- E.Y.T ERP | Phase 3 Procurement Engine
-- PostgreSQL

CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_code VARCHAR(50) NOT NULL UNIQUE,
    name_fa VARCHAR(250) NOT NULL,
    name_en VARCHAR(250),
    supplier_type VARCHAR(40) NOT NULL DEFAULT 'MATERIAL'
        CHECK (supplier_type IN ('MATERIAL','SERVICE','SUBCONTRACTOR','OTHER')),
    tax_id VARCHAR(100),
    phone VARCHAR(50),
    payment_terms_days INTEGER NOT NULL DEFAULT 0 CHECK (payment_terms_days >= 0),
    credit_limit NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS supplier_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    supplier_sku VARCHAR(100),
    last_price NUMERIC(18,4),
    currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
    lead_time_days INTEGER CHECK (lead_time_days >= 0),
    minimum_order_quantity NUMERIC(18,6) CHECK (minimum_order_quantity >= 0),
    is_preferred BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (supplier_id, product_id)
);

CREATE TABLE IF NOT EXISTS purchase_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_no VARCHAR(80) NOT NULL UNIQUE,
    requested_by UUID,
    needed_by DATE,
    status VARCHAR(25) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','SUBMITTED','APPROVED','REJECTED','PARTIALLY_ORDERED','ORDERED','CANCELLED')),
    priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL'
        CHECK (priority IN ('LOW','NORMAL','HIGH','URGENT')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    approved_by UUID
);

CREATE TABLE IF NOT EXISTS purchase_request_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_request_id UUID NOT NULL REFERENCES purchase_requests(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    requested_quantity NUMERIC(18,6) NOT NULL CHECK (requested_quantity > 0),
    warehouse_id UUID REFERENCES warehouses(id),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS supplier_quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_no VARCHAR(80) NOT NULL UNIQUE,
    purchase_request_id UUID REFERENCES purchase_requests(id),
    supplier_id UUID NOT NULL REFERENCES suppliers(id),
    quote_date DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'RECEIVED'
        CHECK (status IN ('REQUESTED','RECEIVED','SELECTED','REJECTED','EXPIRED')),
    payment_terms_days INTEGER CHECK (payment_terms_days >= 0),
    delivery_days INTEGER CHECK (delivery_days >= 0),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS supplier_quote_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES supplier_quotes(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(18,4) NOT NULL CHECK (unit_price >= 0),
    discount_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (discount_percent BETWEEN 0 AND 100),
    tax_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (tax_percent BETWEEN 0 AND 100),
    promised_date DATE
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_no VARCHAR(80) NOT NULL UNIQUE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id),
    purchase_request_id UUID REFERENCES purchase_requests(id),
    quote_id UUID REFERENCES supplier_quotes(id),
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_date DATE,
    status VARCHAR(25) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','PENDING_APPROVAL','APPROVED','SENT','PARTIALLY_RECEIVED','RECEIVED','CANCELLED','CLOSED')),
    currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
    subtotal NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    discount_total NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (discount_total >= 0),
    tax_total NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (tax_total >= 0),
    total_amount NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    created_by UUID,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    ordered_quantity NUMERIC(18,6) NOT NULL CHECK (ordered_quantity > 0),
    received_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (received_quantity >= 0),
    unit_price NUMERIC(18,4) NOT NULL CHECK (unit_price >= 0),
    discount_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (discount_percent BETWEEN 0 AND 100),
    tax_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (tax_percent BETWEEN 0 AND 100),
    expected_date DATE
);

CREATE TABLE IF NOT EXISTS goods_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_no VARCHAR(80) NOT NULL UNIQUE,
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id),
    supplier_id UUID NOT NULL REFERENCES suppliers(id),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    receipt_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    status VARCHAR(20) NOT NULL DEFAULT 'RECEIVED'
        CHECK (status IN ('RECEIVED','QC_HOLD','ACCEPTED','PARTIAL','REJECTED','CANCELLED')),
    supplier_document_no VARCHAR(100),
    received_by UUID,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS goods_receipt_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goods_receipt_id UUID NOT NULL REFERENCES goods_receipts(id) ON DELETE CASCADE,
    purchase_order_item_id UUID NOT NULL REFERENCES purchase_order_items(id),
    product_id UUID NOT NULL REFERENCES products(id),
    received_quantity NUMERIC(18,6) NOT NULL CHECK (received_quantity > 0),
    accepted_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (accepted_quantity >= 0),
    rejected_quantity NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (rejected_quantity >= 0),
    lot_id UUID REFERENCES inventory_lots(id),
    qc_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (qc_status IN ('PENDING','PASS','FAIL','HOLD'))
);

CREATE INDEX IF NOT EXISTS idx_supplier_products_product ON supplier_products(product_id);
CREATE INDEX IF NOT EXISTS idx_purchase_requests_status ON purchase_requests(status, priority);
CREATE INDEX IF NOT EXISTS idx_quotes_request ON supplier_quotes(purchase_request_id);
CREATE INDEX IF NOT EXISTS idx_quotes_supplier ON supplier_quotes(supplier_id);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_status ON purchase_orders(supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_expected ON purchase_orders(expected_date, status);
CREATE INDEX IF NOT EXISTS idx_receipts_po ON goods_receipts(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_receipt_items_product ON goods_receipt_items(product_id);
