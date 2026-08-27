-- E.Y.T ERP | Phase 1 Master Data Foundation
-- PostgreSQL

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS product_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES product_categories(id),
    code VARCHAR(50) NOT NULL UNIQUE,
    name_fa VARCHAR(200) NOT NULL,
    name_en VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(30) NOT NULL UNIQUE,
    name_fa VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    precision_digits SMALLINT NOT NULL DEFAULT 0 CHECK (precision_digits BETWEEN 0 AND 6),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_fa VARCHAR(100) NOT NULL,
    brand_en VARCHAR(100),
    model_fa VARCHAR(150) NOT NULL,
    model_en VARCHAR(150),
    generation VARCHAR(100),
    engine VARCHAR(100),
    year_from SMALLINT,
    year_to SMALLINT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (brand_fa, model_fa, generation, engine)
);

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(80) NOT NULL UNIQUE,
    name_fa VARCHAR(250) NOT NULL,
    name_en VARCHAR(250),
    category_id UUID NOT NULL REFERENCES product_categories(id),
    unit_id UUID NOT NULL REFERENCES units(id),
    barcode VARCHAR(100) UNIQUE,
    standard_cost NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (standard_cost >= 0),
    selling_price NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (selling_price >= 0),
    minimum_margin_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (minimum_margin_percent >= 0),
    reorder_point NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (reorder_point >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS product_vehicle_applications (
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    notes TEXT,
    PRIMARY KEY (product_id, vehicle_id)
);

CREATE TABLE IF NOT EXISTS product_oem_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    oem_number VARCHAR(120) NOT NULL,
    source VARCHAR(100),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (product_id, oem_number)
);

CREATE TABLE IF NOT EXISTS boms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','ACTIVE','INACTIVE')),
    effective_from DATE,
    effective_to DATE,
    notes TEXT,
    UNIQUE (product_id, version)
);

CREATE TABLE IF NOT EXISTS bom_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bom_id UUID NOT NULL REFERENCES boms(id) ON DELETE CASCADE,
    component_product_id UUID NOT NULL REFERENCES products(id),
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    scrap_percent NUMERIC(7,3) NOT NULL DEFAULT 0 CHECK (scrap_percent >= 0),
    operation_sequence INTEGER,
    UNIQUE (bom_id, component_product_id, operation_sequence)
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);
CREATE INDEX IF NOT EXISTS idx_oem_numbers_number ON product_oem_numbers(oem_number);
CREATE INDEX IF NOT EXISTS idx_boms_product_status ON boms(product_id, status);
