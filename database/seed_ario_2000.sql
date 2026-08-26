-- E.Y.T ERP reference seed: MO-ARIO-0001

INSERT INTO production_orders
(order_no, product_code, product_name, target_qty, order_date, status, notes)
VALUES
('MO-ARIO-0001', 'ARY-TRE-BODY', 'تنه سیبک فرمان آریو', 2000, CURRENT_DATE, 'planned', 'Reference production order for E.Y.T production flow')
ON CONFLICT (order_no) DO NOTHING;

INSERT INTO material_lots
(production_order_id, material_code, material_name, specification, diameter_mm, quantity, unit, supplier_name, purchase_cost, received_date)
SELECT id, 'CK45-24', 'فولاد CK45', 'Round bar', 24, 0, 'kg', NULL, 0, CURRENT_DATE
FROM production_orders
WHERE order_no = 'MO-ARIO-0001'
AND NOT EXISTS (
    SELECT 1 FROM material_lots ml WHERE ml.production_order_id = production_orders.id AND ml.material_code = 'CK45-24'
);

INSERT INTO production_operations
(production_order_id, sequence_no, operation_code, operation_name, input_qty, status)
SELECT id, v.seq, v.code, v.name, CASE WHEN v.seq = 1 THEN 2000 ELSE 0 END, 'pending'
FROM production_orders po
CROSS JOIN (VALUES
    (1, 'CUT', 'برش'),
    (2, 'FORGE', 'فورج کاری'),
    (3, 'DRILL', 'سوراخ کاری'),
    (4, 'CNC', 'ماشین کاری CNC'),
    (5, 'TAP', 'رزوه و قلاویز'),
    (6, 'BLACK_PLATE', 'آبکاری مشکی'),
    (7, 'FINAL_QC', 'کنترل کیفیت نهایی')
) AS v(seq, code, name)
WHERE po.order_no = 'MO-ARIO-0001'
AND NOT EXISTS (
    SELECT 1 FROM production_operations p WHERE p.production_order_id = po.id AND p.sequence_no = v.seq
);
