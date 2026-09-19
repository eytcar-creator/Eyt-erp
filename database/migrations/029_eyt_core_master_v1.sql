-- EYT Core Master Schema v1.0
-- Migration 023
-- Purpose: establish the single master-data layer for Product, Vehicle, Customer,
-- Supplier, Warehouse and vehicle fitment, then bridge Order Center and Production
-- without deleting or rewriting legacy data.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION eyt_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS eyt_product_master (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sku text NOT NULL UNIQUE,
  code128 text UNIQUE,
  product_name_fa text NOT NULL,
  product_name_en text,
  product_type text NOT NULL DEFAULT 'FINISHED',
  category text,
  brand text NOT NULL DEFAULT 'EYT',
  unit text NOT NULL DEFAULT 'PCS',
  status text NOT NULL DEFAULT 'ACTIVE',
  description text,
  standard_cost numeric(18,2) NOT NULL DEFAULT 0,
  last_cost numeric(18,2) NOT NULL DEFAULT 0,
  retail_price numeric(18,2) NOT NULL DEFAULT 0,
  distribution_price numeric(18,2) NOT NULL DEFAULT 0,
  wholesale_price numeric(18,2) NOT NULL DEFAULT 0,
  min_stock numeric(18,3) NOT NULL DEFAULT 0,
  reorder_point numeric(18,3) NOT NULL DEFAULT 0,
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eyt_vehicle_master (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  make text NOT NULL,
  model text NOT NULL,
  generation text,
  trim text,
  model_year_from integer,
  model_year_to integer,
  engine text,
  transmission text,
  fuel_type text,
  country text,
  status text NOT NULL DEFAULT 'ACTIVE',
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_eyt_vehicle_years
    CHECK (model_year_to IS NULL OR model_year_from IS NULL OR model_year_to >= model_year_from)
);

CREATE TABLE IF NOT EXISTS eyt_product_vehicle_fitment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES eyt_product_master(id),
  vehicle_id uuid NOT NULL REFERENCES eyt_vehicle_master(id),
  position text,
  fitment_note text,
  oe_numbers text[] NOT NULL DEFAULT ARRAY[]::text[],
  status text NOT NULL DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(product_id, vehicle_id, position)
);

CREATE TABLE IF NOT EXISTS eyt_customer_master (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_code text NOT NULL UNIQUE,
  customer_type text NOT NULL DEFAULT 'END_CUSTOMER',
  legal_name text,
  first_name text,
  last_name text,
  mobile text,
  phone text,
  email text,
  province text,
  city text,
  area text,
  postal_code text,
  address text,
  source_channel text,
  status text NOT NULL DEFAULT 'ACTIVE',
  marketing_opt_in boolean NOT NULL DEFAULT false,
  notes text,
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eyt_supplier_master (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_code text NOT NULL UNIQUE,
  supplier_type text NOT NULL DEFAULT 'SUPPLIER',
  legal_name text NOT NULL,
  contact_name text,
  mobile text,
  phone text,
  email text,
  province text,
  city text,
  address text,
  tax_id text,
  status text NOT NULL DEFAULT 'ACTIVE',
  notes text,
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eyt_warehouse_master (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  warehouse_code text NOT NULL UNIQUE,
  warehouse_name text NOT NULL,
  warehouse_type text NOT NULL DEFAULT 'GENERAL',
  city text,
  address text,
  status text NOT NULL DEFAULT 'ACTIVE',
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eyt_customer_vehicle (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES eyt_customer_master(id),
  vehicle_id uuid NOT NULL REFERENCES eyt_vehicle_master(id),
  vin text,
  plate_no text,
  nickname text,
  is_primary boolean NOT NULL DEFAULT false,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(customer_id, vehicle_id, plate_no)
);

CREATE TABLE IF NOT EXISTS eyt_product_alias (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES eyt_product_master(id),
  alias_code text NOT NULL,
  alias_type text NOT NULL DEFAULT 'OEM',
  source_name text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(alias_type, alias_code)
);

-- Bridges: preserve legacy identifiers while making UUID master IDs canonical.
ALTER TABLE sales_orders
  ADD COLUMN IF NOT EXISTS customer_master_id uuid REFERENCES eyt_customer_master(id);

ALTER TABLE sales_order_items
  ADD COLUMN IF NOT EXISTS product_master_id uuid REFERENCES eyt_product_master(id);

ALTER TABLE production_orders
  ADD COLUMN IF NOT EXISTS product_master_id uuid REFERENCES eyt_product_master(id);

ALTER TABLE production_orders
  ADD COLUMN IF NOT EXISTS customer_master_id uuid REFERENCES eyt_customer_master(id);

CREATE INDEX IF NOT EXISTS idx_eyt_product_vehicle_product
  ON eyt_product_vehicle_fitment(product_id);

CREATE INDEX IF NOT EXISTS idx_eyt_product_vehicle_vehicle
  ON eyt_product_vehicle_fitment(vehicle_id);

CREATE INDEX IF NOT EXISTS idx_eyt_customer_mobile
  ON eyt_customer_master(mobile);

CREATE INDEX IF NOT EXISTS idx_eyt_supplier_name
  ON eyt_supplier_master(legal_name);

CREATE INDEX IF NOT EXISTS idx_eyt_customer_vehicle_customer
  ON eyt_customer_vehicle(customer_id);

CREATE INDEX IF NOT EXISTS idx_eyt_customer_vehicle_vehicle
  ON eyt_customer_vehicle(vehicle_id);

CREATE INDEX IF NOT EXISTS idx_sales_orders_customer_master
  ON sales_orders(customer_master_id);

CREATE INDEX IF NOT EXISTS idx_sales_order_items_product_master
  ON sales_order_items(product_master_id);

CREATE INDEX IF NOT EXISTS idx_production_orders_product_master
  ON production_orders(product_master_id);

CREATE INDEX IF NOT EXISTS idx_production_orders_customer_master
  ON production_orders(customer_master_id);

DROP TRIGGER IF EXISTS trg_eyt_product_updated_at ON eyt_product_master;
CREATE TRIGGER trg_eyt_product_updated_at
BEFORE UPDATE ON eyt_product_master
FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();

DROP TRIGGER IF EXISTS trg_eyt_vehicle_updated_at ON eyt_vehicle_master;
CREATE TRIGGER trg_eyt_vehicle_updated_at
BEFORE UPDATE ON eyt_vehicle_master
FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();

DROP TRIGGER IF EXISTS trg_eyt_fitment_updated_at ON eyt_product_vehicle_fitment;
CREATE TRIGGER trg_eyt_fitment_updated_at
BEFORE UPDATE ON eyt_product_vehicle_fitment
FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();

DROP TRIGGER IF EXISTS trg_eyt_customer_updated_at ON eyt_customer_master;
CREATE TRIGGER trg_eyt_customer_updated_at
BEFORE UPDATE ON eyt_customer_master
FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();

DROP TRIGGER IF EXISTS trg_eyt_supplier_updated_at ON eyt_supplier_master;
CREATE TRIGGER trg_eyt_supplier_updated_at
BEFORE UPDATE ON eyt_supplier_master
FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();

DROP TRIGGER IF EXISTS trg_eyt_warehouse_updated_at ON eyt_warehouse_master;
CREATE TRIGGER trg_eyt_warehouse_updated_at
BEFORE UPDATE ON eyt_warehouse_master
FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();

DROP TRIGGER IF EXISTS trg_eyt_customer_vehicle_updated_at ON eyt_customer_vehicle;
CREATE TRIGGER trg_eyt_customer_vehicle_updated_at
BEFORE UPDATE ON eyt_customer_vehicle
FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();
