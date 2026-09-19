-- EYT reference BOM/routing seed
-- Uses Product Master IDs resolved by SKU. Safe to run after master data exists.

-- Example finished product: ARIO steering ball joint.
-- Component SKUs are intentionally explicit so missing master records fail loudly.
WITH p AS (
  SELECT id, sku FROM eyt_product_master
  WHERE sku IN (
    'ARY-TRE-BODY','ARY-TRE-NUT','ARY-TRE-GREASE','ARY-TRE-PIN',
    'ARY-TRE-BOOT','ARY-TRE-SPRING','ARY-TRE-RING','ARY-TRE-RUBBER',
    'ARY-TRE-WASHER','ARY-TRE-PACK'
  )
)
INSERT INTO eyt_material_cost_snapshot(product_id, unit_cost, source, notes)
SELECT id, COALESCE(last_cost, standard_cost, 0), 'MASTER',
       'Initial EYT Ario reference cost snapshot'
FROM p
WHERE NOT EXISTS (
  SELECT 1 FROM eyt_material_cost_snapshot s
  WHERE s.product_id = p.id
    AND s.source = 'MASTER'
);

WITH finished AS (
  SELECT id FROM eyt_product_master WHERE sku = 'ARY-TRE-FG'
),
bom AS (
  INSERT INTO eyt_bom(product_id, bom_code, version, status, notes)
  SELECT id, 'BOM-ARY-TRE-FG', 1, 'DRAFT',
         'Reference BOM; validate quantities against approved drawing before release'
  FROM finished
  WHERE NOT EXISTS (
    SELECT 1 FROM eyt_bom WHERE product_id = finished.id AND version = 1
  )
  RETURNING id
)
INSERT INTO eyt_bom_item(bom_id, component_product_id, quantity_per, sequence_no, notes)
SELECT bom.id, p.id, x.qty, x.seq, 'Reference Ario steering ball joint component'
FROM bom
JOIN (VALUES
  ('ARY-TRE-BODY',1.000,10),
  ('ARY-TRE-NUT',1.000,20),
  ('ARY-TRE-GREASE',1.000,30),
  ('ARY-TRE-PIN',1.000,40),
  ('ARY-TRE-BOOT',1.000,50),
  ('ARY-TRE-SPRING',1.000,60),
  ('ARY-TRE-RING',1.000,70),
  ('ARY-TRE-RUBBER',1.000,80),
  ('ARY-TRE-WASHER',1.000,90),
  ('ARY-TRE-PACK',1.000,100)
) AS x(sku,qty,seq) ON true
JOIN eyt_product_master p ON p.sku = x.sku;

WITH finished AS (
  SELECT id FROM eyt_product_master WHERE sku = 'ARY-TRE-FG'
),
routing AS (
  INSERT INTO eyt_routing(product_id, routing_code, version, status, notes)
  SELECT id, 'RT-ARY-TRE-FG', 1, 'DRAFT',
         'Reference routing from existing Ario seed; validate with production'
  FROM finished
  WHERE NOT EXISTS (
    SELECT 1 FROM eyt_routing WHERE product_id = finished.id AND version = 1
  )
  RETURNING id
)
INSERT INTO eyt_routing_operation(
  routing_id, sequence_no, operation_code, operation_name_fa,
  make_or_buy, planned_days, capacity_per_day, qc_required
)
SELECT routing.id, x.seq, x.code, x.name, x.make_buy, x.days, x.capacity, x.qc
FROM routing
JOIN (VALUES
  (10,'CUT','برش','MAKE',0.5,400.0,false),
  (20,'FORGE','فورج کاری','BUY',7.0,400.0,false),
  (30,'DRILL','سوراخ کاری','MAKE',1.0,350.0,false),
  (40,'CNC','ماشین کاری CNC','BUY',7.0,350.0,false),
  (50,'TAP','رزوه و قلاویز','MAKE',5.0,800.0,false),
  (60,'BLACK_PLATE','آبکاری مشکی','BUY',6.0,700.0,false),
  (70,'FINAL_ASSEMBLY','مونتاژ نهایی','MAKE',1.0,300.0,true),
  (80,'FINAL_QC','کنترل کیفیت نهایی','MAKE',1.0,300.0,true)
) AS x(seq,code,name,make_buy,days,capacity,qc) ON true;
