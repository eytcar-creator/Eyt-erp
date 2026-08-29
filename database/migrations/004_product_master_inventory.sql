-- E.Y.T ERP | Migration 004 | Product Master + Inventory operational foundation
-- PostgreSQL / idempotent
BEGIN;

CREATE TABLE IF NOT EXISTS product_categories (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(60) NOT NULL UNIQUE,
    name_fa VARCHAR(150) NOT NULL,
    name_en VARCHAR(150),
    parent_id BIGINT REFERENCES product_categories(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(100) NOT NULL UNIQUE,
    product_code VARCHAR(100) NOT NULL UNIQUE,
    name_fa VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    category_id BIGINT REFERENCES product_categories(id) ON DELETE SET NULL,
    product_type VARCHAR(40) NOT NULL DEFAULT 'FINISHED_GOOD',
    brand VARCHAR(100) DEFAULT 'E.Y.T',
    unit VARCHAR(20) NOT NULL DEFAULT 'PCS',
    barcode VARCHAR(100) UNIQUE,
    oem_code VARCHAR(150),
    specification VARCHAR(500),
    weight_kg NUMERIC(12,4) CHECK (weight_kg IS NULL OR weight_kg >= 0),
    purchase_price NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (purchase_price >= 0),
    sale_price NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (sale_price >= 0),
    reorder_point NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (reorder_point >= 0),
    min_stock NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (min_stock >= 0),
    max_stock NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (max_stock >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (max_stock = 0 OR max_stock >= min_stock)
);

CREATE TABLE IF NOT EXISTS product_vehicle_fitments (
    id BIGSERIAL PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    make VARCHAR(100) NOT NULL,
    model VARCHAR(150) NOT NULL,
    trim VARCHAR(150),
    year_from SMALLINT,
    year_to SMALLINT,
    notes TEXT,
    UNIQUE(product_id, make, model, trim, year_from, year_to)
);

CREATE TABLE IF NOT EXISTS product_aliases (
    id BIGSERIAL PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    alias VARCHAR(150) NOT NULL,
    alias_type VARCHAR(40) NOT NULL DEFAULT 'MARKET',
    UNIQUE(alias, alias_type)
);

CREATE TABLE IF NOT EXISTS warehouses (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(60) NOT NULL UNIQUE,
    name_fa VARCHAR(150) NOT NULL,
    name_en VARCHAR(150),
    location VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id BIGSERIAL PRIMARY KEY,
    product_code VARCHAR(100) NOT NULL REFERENCES products(product_code),
    warehouse_code VARCHAR(60) NOT NULL REFERENCES warehouses(code),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(20) NOT NULL DEFAULT 'PCS',
    transaction_type VARCHAR(30) NOT NULL,
    reference_type VARCHAR(50),
    reference_id VARCHAR(100),
    unit_cost NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (transaction_type IN ('RECEIPT','ISSUE','TRANSFER_OUT','TRANSFER_IN','CONSUMPTION','RETURN','SCRAP','PRODUCTION_RECEIPT','ADJUSTMENT'))
);

CREATE TABLE IF NOT EXISTS inventory_reservations (
    id BIGSERIAL PRIMARY KEY,
    product_code VARCHAR(100) NOT NULL REFERENCES products(product_code),
    warehouse_code VARCHAR(60) NOT NULL REFERENCES warehouses(code),
    reference_type VARCHAR(50) NOT NULL,
    reference_id VARCHAR(100) NOT NULL,
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'RESERVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('RESERVED','RELEASED','CONSUMED','CANCELLED'))
);

INSERT INTO product_categories(code,name_fa,name_en) VALUES
 ('SUSPENSION','جلوبندی و تعلیق','Suspension'),
 ('STEERING_BALL_JOINT','سیبک فرمان','Tie Rod End'),
 ('CONTROL_ARM_BALL_JOINT','سیبک طبق','Control Arm Ball Joint'),
 ('BUSH','بوش','Bush'),
 ('STABILIZER','موج‌گیر و متعلقات','Stabilizer'),
 ('ENGINE_MOUNT','دسته موتور','Engine Mount'),
 ('RAW_MATERIAL','مواد اولیه','Raw Material'),
 ('SERVICE','خدمات تولید','Production Service')
ON CONFLICT (code) DO NOTHING;

INSERT INTO warehouses(code,name_fa,name_en,location) VALUES
 ('TABRIZ-ASSEMBLY','کارگاه مونتاژ تبریز','Tabriz Assembly','Tabriz'),
 ('TABRIZ-WORKSHOP-2','کارگاه تولید ۲ تبریز','Tabriz Workshop 2','Tabriz'),
 ('TEHRAN-SHOP','فروشگاه تهران','Tehran Shop','Tehran'),
 ('MAIN','انبار اصلی','Main Warehouse','Main')
ON CONFLICT (code) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active);
CREATE INDEX IF NOT EXISTS idx_products_oem ON products(oem_code);
CREATE INDEX IF NOT EXISTS idx_fitments_vehicle ON product_vehicle_fitments(make,model);
CREATE INDEX IF NOT EXISTS idx_aliases_product ON product_aliases(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_tx_product_warehouse ON inventory_transactions(product_code,warehouse_code,created_at);
CREATE INDEX IF NOT EXISTS idx_inventory_tx_reference ON inventory_transactions(reference_type,reference_id);
CREATE INDEX IF NOT EXISTS idx_inventory_res_product_warehouse ON inventory_reservations(product_code,warehouse_code,status);

COMMIT;
