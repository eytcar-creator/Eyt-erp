-- EYT reference BOM/routing seed v1
-- This seed does not invent an unverified finished-product SKU.
-- The existing Ario reference order is for ARY-TRE-BODY (intermediate/body).
-- Create the approved finished-product and component master records first,
-- then populate the BOM using their real SKUs.

-- Routing for the existing reference product ARY-TRE-BODY.
-- It mirrors the routing already present in seed_ario_2000.sql.
WITH finished AS (
  SELECT id FROM eyt_product_master WHERE sku = 'ARY-TRE-BODY'
),
routing AS (
  INSERT INTO eyt_routing(product_id, routing_code, version, status, notes)
  SELECT id, 'RT-ARY-TRE-BODY', 1, 'DRAFT',
         'Reference routing derived from existing Ario production seed; validate before release'
  FROM finished
  WHERE NOT EXISTS (
    SELECT 1 FROM eyt_routing
    WHERE product_id = finished.id AND version = 1
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
  (70,'FINAL_QC','کنترل کیفیت نهایی','MAKE',1.0,300.0,true)
) AS x(seq,code,name,make_buy,days,capacity,qc) ON true
WHERE NOT EXISTS (
  SELECT 1 FROM eyt_routing_operation ro
  WHERE ro.routing_id = routing.id AND ro.sequence_no = x.seq
);

-- Approved BOM components must be added only after their Product Master records
-- exist. Example component mapping for the final assembled product:
-- BODY, NUT, GREASE, PIN, BOOT, SPRING, RING, RUBBER, WASHER, PACKAGING.
