-- E.Y.T ERP | Migration 021 | Customer & Market Engine v1
-- Consumer -> Vehicle -> SKU -> Order -> Installation -> Payment -> Repeat Purchase
BEGIN;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS customer_type VARCHAR(30) NOT NULL DEFAULT 'CONSUMER';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS source VARCHAR(80);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS marketing_source VARCHAR(120);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS notes TEXT;

CREATE TABLE IF NOT EXISTS customer_vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    vehicle_id UUID NOT NULL REFERENCES vehicle_master(id) ON DELETE RESTRICT,
    plate_no VARCHAR(30),
    model_year VARCHAR(20),
    mileage_km INTEGER CHECK (mileage_km IS NULL OR mileage_km >= 0),
    vin VARCHAR(40),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, vehicle_id, plate_no)
);

CREATE TABLE IF NOT EXISTS mechanics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mechanic_code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(80),
    city VARCHAR(100),
    area VARCHAR(120),
    specialty VARCHAR(150),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parts_stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(80),
    city VARCHAR(100),
    area VARCHAR(120),
    address TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    mechanic_id UUID REFERENCES mechanics(id) ON DELETE SET NULL,
    parts_store_id UUID REFERENCES parts_stores(id) ON DELETE SET NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'DIRECT',
    order_id UUID REFERENCES sales_orders(id) ON DELETE SET NULL,
    commission_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (commission_amount >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    customer_vehicle_id UUID REFERENCES customer_vehicles(id) ON DELETE SET NULL,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    order_id UUID REFERENCES sales_orders(id) ON DELETE SET NULL,
    mechanic_id UUID REFERENCES mechanics(id) ON DELETE SET NULL,
    installed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    quantity NUMERIC(18,6) NOT NULL DEFAULT 1 CHECK (quantity > 0),
    mileage_km INTEGER CHECK (mileage_km IS NULL OR mileage_km >= 0),
    warranty_until DATE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS purchase_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    customer_vehicle_id UUID REFERENCES customer_vehicles(id) ON DELETE SET NULL,
    order_id UUID REFERENCES sales_orders(id) ON DELETE SET NULL,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) NOT NULL DEFAULT 'DIRECT',
    next_expected_purchase DATE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS repeat_purchase_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    customer_vehicle_id UUID REFERENCES customer_vehicles(id) ON DELETE SET NULL,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    last_purchase_id UUID REFERENCES purchase_history(id) ON DELETE SET NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    contacted_at TIMESTAMPTZ,
    completed_order_id UUID REFERENCES sales_orders(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_customer_vehicles_customer ON customer_vehicles(customer_id);
CREATE INDEX IF NOT EXISTS ix_customer_vehicles_vehicle ON customer_vehicles(vehicle_id);
CREATE INDEX IF NOT EXISTS ix_mechanics_city_status ON mechanics(city,status);
CREATE INDEX IF NOT EXISTS ix_parts_stores_city_status ON parts_stores(city,status);
CREATE INDEX IF NOT EXISTS ix_referrals_customer ON referrals(customer_id,created_at);
CREATE INDEX IF NOT EXISTS ix_installations_customer ON installations(customer_id,installed_at DESC);
CREATE INDEX IF NOT EXISTS ix_purchase_history_customer ON purchase_history(customer_id,purchased_at DESC);
CREATE INDEX IF NOT EXISTS ix_repeat_purchase_due ON repeat_purchase_reminders(status,due_date);

COMMIT;
