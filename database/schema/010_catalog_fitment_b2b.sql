-- E.Y.T ERP | Phase 10 Product Catalog, Vehicle Fitment & B2B Ordering
-- PostgreSQL

CREATE TABLE IF NOT EXISTS vehicle_brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name_fa VARCHAR(150) NOT NULL UNIQUE,
    name_en VARCHAR(150),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS vehicle_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID NOT NULL REFERENCES vehicle_brands(id),
    model_name_fa VARCHAR(150) NOT NULL,
    model_name_en VARCHAR(150),
    generation VARCHAR(100),
    engine_code VARCHAR(100),
    production_from SMALLINT,
    production_to SMALLINT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (brand_id, model_name_fa, generation)
);

CREATE TABLE IF NOT EXISTS product_fitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    vehicle_model_id UUID NOT NULL REFERENCES vehicle_models(id) ON DELETE CASCADE,
    position VARCHAR(50),
    side VARCHAR(20),
    fitment_note TEXT,
    oem_number VARCHAR(120),
    is_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(product_id, vehicle_model_id, position, side)
);

CREATE TABLE IF NOT EXISTS product_cross_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    reference_type VARCHAR(30) NOT NULL CHECK (reference_type IN ('OEM','AFTERMARKET','CUSTOMER_SKU')),
    reference_number VARCHAR(150) NOT NULL,
    brand_name VARCHAR(150),
    notes TEXT,
    UNIQUE(reference_type, reference_number, brand_name)
);

CREATE TABLE IF NOT EXISTS product_kits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kit_product_id UUID NOT NULL REFERENCES products(id) UNIQUE,
    kit_name_fa VARCHAR(250) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS product_kit_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kit_id UUID NOT NULL REFERENCES product_kits(id) ON DELETE CASCADE,
    component_product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    UNIQUE(kit_id, component_product_id)
);

CREATE TABLE IF NOT EXISTS b2b_price_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name_fa VARCHAR(200) NOT NULL,
    customer_type VARCHAR(30),
    currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS b2b_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    price_list_id UUID NOT NULL REFERENCES b2b_price_lists(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    unit_price NUMERIC(18,4) NOT NULL CHECK (unit_price >= 0),
    minimum_quantity NUMERIC(18,6) NOT NULL DEFAULT 1 CHECK (minimum_quantity > 0),
    discount_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (discount_percent BETWEEN 0 AND 100),
    UNIQUE(price_list_id, product_id, minimum_quantity)
);

CREATE TABLE IF NOT EXISTS b2b_order_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_no VARCHAR(80) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status VARCHAR(25) NOT NULL DEFAULT 'RECEIVED'
        CHECK(status IN ('RECEIVED','VALIDATING','APPROVED','REJECTED','CONVERTED','CANCELLED')),
    channel VARCHAR(30) NOT NULL DEFAULT 'WEB'
        CHECK(channel IN ('WEB','API','WHATSAPP','PHONE','OTHER')),
    external_reference VARCHAR(150),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS b2b_order_request_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES b2b_order_requests(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL CHECK(quantity > 0),
    requested_unit_price NUMERIC(18,4),
    approved_unit_price NUMERIC(18,4)
);

CREATE INDEX IF NOT EXISTS idx_vehicle_models_brand ON vehicle_models(brand_id);
CREATE INDEX IF NOT EXISTS idx_fitments_vehicle ON product_fitments(vehicle_model_id);
CREATE INDEX IF NOT EXISTS idx_fitments_product ON product_fitments(product_id);
CREATE INDEX IF NOT EXISTS idx_crossrefs_product ON product_cross_references(product_id);
CREATE INDEX IF NOT EXISTS idx_b2b_prices_product ON b2b_prices(product_id);
CREATE INDEX IF NOT EXISTS idx_b2b_requests_customer_status ON b2b_order_requests(customer_id, status);
