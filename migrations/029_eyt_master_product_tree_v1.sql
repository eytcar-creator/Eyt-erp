-- EYT Master Product Tree v1.0
-- Migration 029
-- Canonical product taxonomy, physical-part identity and annual capacity policy.
-- Additive migration; existing Product Master/BOM data is preserved.

CREATE TABLE IF NOT EXISTS eyt_product_family (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL UNIQUE,
  name_fa text NOT NULL,
  name_en text NOT NULL,
  source_scope text NOT NULL DEFAULT 'CORE',
  status text NOT NULL DEFAULT 'ACTIVE',
  sort_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eyt_product_subfamily (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id uuid NOT NULL REFERENCES eyt_product_family(id),
  code text NOT NULL UNIQUE,
  name_fa text NOT NULL,
  name_en text NOT NULL,
  default_product_type text NOT NULL DEFAULT 'FINISHED',
  status text NOT NULL DEFAULT 'ACTIVE',
  sort_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(family_id, name_fa)
);

CREATE TABLE IF NOT EXISTS eyt_physical_part (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  part_key text NOT NULL UNIQUE,
  name_fa text NOT NULL,
  material text,
  manufacturing_class text NOT NULL DEFAULT 'ASSEMBLY',
  make_or_buy text NOT NULL DEFAULT 'MAKE',
  notes text,
  status text NOT NULL DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE eyt_product_master
  ADD COLUMN IF NOT EXISTS family_id uuid REFERENCES eyt_product_family(id);
ALTER TABLE eyt_product_master
  ADD COLUMN IF NOT EXISTS subfamily_id uuid REFERENCES eyt_product_subfamily(id);
ALTER TABLE eyt_product_master
  ADD COLUMN IF NOT EXISTS physical_part_id uuid REFERENCES eyt_physical_part(id);
ALTER TABLE eyt_product_master
  ADD COLUMN IF NOT EXISTS procurement_mode text NOT NULL DEFAULT 'MAKE_OR_BUY';
ALTER TABLE eyt_product_master
  ADD COLUMN IF NOT EXISTS annual_min_qty numeric(18,3) NOT NULL DEFAULT 0;
ALTER TABLE eyt_product_master
  ADD COLUMN IF NOT EXISTS annual_normal_max_qty numeric(18,3) NOT NULL DEFAULT 0;
ALTER TABLE eyt_product_master
  ADD COLUMN IF NOT EXISTS customer_order_override_allowed boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS eyt_product_capacity_policy (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id uuid NOT NULL REFERENCES eyt_product_family(id),
  annual_min_qty numeric(18,3) NOT NULL DEFAULT 0,
  annual_normal_max_qty numeric(18,3) NOT NULL DEFAULT 0,
  minimum_mandatory boolean NOT NULL DEFAULT true,
  confirmed_order_override_allowed boolean NOT NULL DEFAULT true,
  effective_from date NOT NULL DEFAULT CURRENT_DATE,
  effective_to date,
  status text NOT NULL DEFAULT 'ACTIVE',
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_capacity_range CHECK (annual_normal_max_qty >= annual_min_qty),
  CONSTRAINT ck_capacity_dates CHECK (effective_to IS NULL OR effective_to >= effective_from),
  UNIQUE(family_id, effective_from)
);

CREATE INDEX IF NOT EXISTS idx_eyt_product_family ON eyt_product_master(family_id);
CREATE INDEX IF NOT EXISTS idx_eyt_product_subfamily ON eyt_product_master(subfamily_id);
CREATE INDEX IF NOT EXISTS idx_eyt_product_physical_part ON eyt_product_master(physical_part_id);
CREATE INDEX IF NOT EXISTS idx_eyt_capacity_family ON eyt_product_capacity_policy(family_id, status);

DROP TRIGGER IF EXISTS trg_eyt_product_family_updated_at ON eyt_product_family;
CREATE TRIGGER trg_eyt_product_family_updated_at
BEFORE UPDATE ON eyt_product_family FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();

DROP TRIGGER IF EXISTS trg_eyt_product_subfamily_updated_at ON eyt_product_subfamily;
CREATE TRIGGER trg_eyt_product_subfamily_updated_at
BEFORE UPDATE ON eyt_product_subfamily FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();

DROP TRIGGER IF EXISTS trg_eyt_physical_part_updated_at ON eyt_physical_part;
CREATE TRIGGER trg_eyt_physical_part_updated_at
BEFORE UPDATE ON eyt_physical_part FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();

DROP TRIGGER IF EXISTS trg_eyt_capacity_policy_updated_at ON eyt_product_capacity_policy;
CREATE TRIGGER trg_eyt_capacity_policy_updated_at
BEFORE UPDATE ON eyt_product_capacity_policy FOR EACH ROW EXECUTE FUNCTION eyt_set_updated_at();

CREATE OR REPLACE FUNCTION eyt_capacity_decision(
  p_family_code text,
  p_annual_planned_qty numeric,
  p_confirmed_customer_order boolean DEFAULT false
)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  v_min numeric;
  v_max numeric;
  v_mandatory boolean;
  v_override boolean;
BEGIN
  SELECT annual_min_qty, annual_normal_max_qty, minimum_mandatory,
         confirmed_order_override_allowed
    INTO v_min, v_max, v_mandatory, v_override
  FROM eyt_product_capacity_policy p
  JOIN eyt_product_family f ON f.id = p.family_id
  WHERE f.code = p_family_code
    AND p.status = 'ACTIVE'
    AND p.effective_from <= CURRENT_DATE
    AND (p.effective_to IS NULL OR p.effective_to >= CURRENT_DATE)
  ORDER BY p.effective_from DESC LIMIT 1;

  IF NOT FOUND THEN RETURN 'NO_POLICY'; END IF;
  IF p_annual_planned_qty < v_min AND v_mandatory THEN RETURN 'BELOW_MANDATORY_MIN'; END IF;
  IF p_annual_planned_qty <= v_max THEN RETURN 'NORMAL_CAPACITY'; END IF;
  IF p_confirmed_customer_order AND v_override THEN RETURN 'CUSTOMER_ORDER_OVERRIDE'; END IF;
  RETURN 'ABOVE_NORMAL_CAPACITY_REVIEW';
END;
$$;

INSERT INTO eyt_product_family(code,name_fa,name_en,source_scope,sort_order)
VALUES
 ('STEERING','فرمان و جلوبندی فرمان','Steering','CORE',10),
 ('FRONT_SUSPENSION','جلوبندی','Front Suspension','CORE',20),
 ('BUSHINGS','بوش‌ها','Bushings','CORE',30),
 ('MOUNTING','دسته‌موتور و متعلقات نصب','Mounting','CORE',40),
 ('BELLOWS_RUBBER','گردگیر و قطعات لاستیکی','Bellows & Rubber','CORE',50),
 ('CONTROL_ARM','طبق و متعلقات طبق','Control Arm','CORE',60),
 ('REPAIR_KITS','کیت‌های تعمیراتی','Repair Kits','CORE',70),
 ('TRADING','بازرگانی','Trading','TRADING',80)
ON CONFLICT (code) DO UPDATE SET
  name_fa=EXCLUDED.name_fa, name_en=EXCLUDED.name_en,
  source_scope=EXCLUDED.source_scope, sort_order=EXCLUDED.sort_order, updated_at=now();

INSERT INTO eyt_product_capacity_policy
  (family_id,annual_min_qty,annual_normal_max_qty,minimum_mandatory,confirmed_order_override_allowed,notes)
SELECT id, 80000, 120000, true, true,
       'Mandatory annual minimum; normal maximum is planning capacity, not a sales ceiling.'
FROM eyt_product_family WHERE code='FRONT_SUSPENSION'
ON CONFLICT (family_id,effective_from) DO UPDATE SET
  annual_min_qty=EXCLUDED.annual_min_qty, annual_normal_max_qty=EXCLUDED.annual_normal_max_qty,
  minimum_mandatory=EXCLUDED.minimum_mandatory,
  confirmed_order_override_allowed=EXCLUDED.confirmed_order_override_allowed,
  notes=EXCLUDED.notes, updated_at=now();

INSERT INTO eyt_product_capacity_policy
  (family_id,annual_min_qty,annual_normal_max_qty,minimum_mandatory,confirmed_order_override_allowed,notes)
SELECT id, 40000, 80000, true, true,
       'Mandatory annual minimum; confirmed customer orders may authorize production above normal capacity.'
FROM eyt_product_family WHERE code='BUSHINGS'
ON CONFLICT (family_id,effective_from) DO UPDATE SET
  annual_min_qty=EXCLUDED.annual_min_qty, annual_normal_max_qty=EXCLUDED.annual_normal_max_qty,
  minimum_mandatory=EXCLUDED.minimum_mandatory,
  confirmed_order_override_allowed=EXCLUDED.confirmed_order_override_allowed,
  notes=EXCLUDED.notes, updated_at=now();

INSERT INTO eyt_product_capacity_policy
  (family_id,annual_min_qty,annual_normal_max_qty,minimum_mandatory,confirmed_order_override_allowed,notes)
SELECT id, 10000, 50000, true, true,
       'Mandatory annual minimum; normal maximum is not a hard order limit.'
FROM eyt_product_family WHERE code='BELLOWS_RUBBER'
ON CONFLICT (family_id,effective_from) DO UPDATE SET
  annual_min_qty=EXCLUDED.annual_min_qty, annual_normal_max_qty=EXCLUDED.annual_normal_max_qty,
  minimum_mandatory=EXCLUDED.minimum_mandatory,
  confirmed_order_override_allowed=EXCLUDED.confirmed_order_override_allowed,
  notes=EXCLUDED.notes, updated_at=now();

INSERT INTO eyt_product_capacity_policy
  (family_id,annual_min_qty,annual_normal_max_qty,minimum_mandatory,confirmed_order_override_allowed,notes)
SELECT id, 5000, 20000, true, true,
       'Mandatory annual minimum; confirmed customer orders may trigger production above normal capacity.'
FROM eyt_product_family WHERE code='MOUNTING'
ON CONFLICT (family_id,effective_from) DO UPDATE SET
  annual_min_qty=EXCLUDED.annual_min_qty, annual_normal_max_qty=EXCLUDED.annual_normal_max_qty,
  minimum_mandatory=EXCLUDED.minimum_mandatory,
  confirmed_order_override_allowed=EXCLUDED.confirmed_order_override_allowed,
  notes=EXCLUDED.notes, updated_at=now();
