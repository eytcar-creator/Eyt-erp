-- E.Y.T ERP reporting views for production true cost

CREATE OR REPLACE VIEW production_cost_summary AS
SELECT
    po.id AS production_order_id,
    po.order_no,
    po.product_code,
    po.product_name,
    po.target_qty,
    COALESCE(ml.material_cost, 0) AS material_cost,
    COALESCE(pc.subcontracting_cost, 0) AS subcontracting_cost,
    COALESCE(pc.transport_cost, 0) AS transport_cost,
    COALESCE(pc.other_cost, 0) AS other_cost,
    COALESCE(cp.prepayment, 0) AS customer_prepayment
FROM production_orders po
LEFT JOIN (
    SELECT production_order_id, SUM(purchase_cost) AS material_cost
    FROM material_lots GROUP BY production_order_id
) ml ON ml.production_order_id = po.id
LEFT JOIN (
    SELECT production_order_id,
           SUM(service_cost) AS subcontracting_cost,
           SUM(transport_cost) AS transport_cost,
           0 AS other_cost
    FROM production_operations GROUP BY production_order_id
) pc ON pc.production_order_id = po.id
LEFT JOIN (
    SELECT production_order_id, SUM(amount) AS prepayment
    FROM customer_prepayments GROUP BY production_order_id
) cp ON cp.production_order_id = po.id;

CREATE OR REPLACE VIEW production_operation_progress AS
SELECT
    po.order_no,
    po.product_name,
    p.sequence_no,
    p.operation_code,
    p.operation_name,
    p.contractor_name,
    p.status,
    p.input_qty,
    p.accepted_qty,
    p.rejected_qty,
    p.waste_qty,
    p.planned_start,
    p.planned_end,
    p.actual_start,
    p.actual_end
FROM production_orders po
JOIN production_operations p ON p.production_order_id = po.id;
