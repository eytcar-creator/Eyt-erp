-- EYT deep smoke-test hardening v1
CREATE OR REPLACE VIEW eyt_bom_cost AS
SELECT b.id AS bom_id,b.product_id,b.version,
       SUM(bi.quantity_per*(1+bi.scrap_percent/100.0)*
           COALESCE(NULLIF(pm.last_cost,0),pm.standard_cost,0)) AS material_cost_per_unit
FROM eyt_bom b
JOIN eyt_bom_item bi ON bi.bom_id=b.id
JOIN eyt_product_master pm ON pm.id=bi.component_product_id
GROUP BY b.id,b.product_id,b.version;

CREATE OR REPLACE VIEW eyt_product_standard_cost AS
SELECT p.id AS product_id,p.sku,p.product_name_fa,
       COALESCE(b.material_cost_per_unit,0) AS bom_material_cost,
       COALESCE(r.operation_cost_per_unit,0) AS routing_operation_cost,
       COALESCE(b.material_cost_per_unit,0)+COALESCE(r.operation_cost_per_unit,0) AS calculated_standard_cost,
       COALESCE(r.planned_days,0) AS production_days
FROM eyt_product_master p
LEFT JOIN LATERAL (SELECT * FROM eyt_bom_cost x WHERE x.product_id=p.id ORDER BY x.version DESC LIMIT 1) b ON true
LEFT JOIN LATERAL (SELECT * FROM eyt_routing_cost x WHERE x.product_id=p.id ORDER BY x.version DESC LIMIT 1) r ON true;

CREATE OR REPLACE VIEW eyt_order_actual_profitability AS
SELECT o.order_no,o.customer_id,o.status,o.created_at,
       COALESCE(SUM(i.quantity*i.unit_price),0) AS sales,
       COALESCE(SUM(i.quantity*COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)),0) AS actual_cogs,
       o.sales_cost,o.logistics_cost,o.finance_cost,o.other_variable_cost,
       COALESCE(SUM(i.quantity*i.unit_price),0)-COALESCE(SUM(i.quantity*COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)),0)
       -o.sales_cost-o.logistics_cost-o.finance_cost-o.other_variable_cost AS contribution_profit,
       CASE WHEN COALESCE(SUM(i.quantity*i.unit_price),0)>0 THEN
         (COALESCE(SUM(i.quantity*i.unit_price),0)-COALESCE(SUM(i.quantity*COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)),0)
          -o.sales_cost-o.logistics_cost-o.finance_cost-o.other_variable_cost)/SUM(i.quantity*i.unit_price)
       ELSE 0 END AS contribution_margin
FROM sales_orders o LEFT JOIN sales_order_items i ON i.sales_order_id=o.id
WHERE o.status NOT IN ('DRAFT','PENDING_CONFIRMATION','CANCELLED','RETURNED')
GROUP BY o.order_no,o.customer_id,o.status,o.created_at,o.sales_cost,o.logistics_cost,o.finance_cost,o.other_variable_cost;

CREATE OR REPLACE VIEW product_profitability_actual AS
SELECT i.product_id,COUNT(DISTINCT i.sales_order_id) AS order_count,COALESCE(SUM(i.quantity),0) AS units_sold,
       COALESCE(SUM(i.quantity*i.unit_price),0) AS sales,
       COALESCE(SUM(i.quantity*COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)),0) AS cogs,
       COALESCE(SUM(i.quantity*(i.unit_price-COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0))),0) AS contribution_profit,
       CASE WHEN COALESCE(SUM(i.quantity*i.unit_price),0)>0
            THEN SUM(i.quantity*(i.unit_price-COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)))/SUM(i.quantity*i.unit_price)
       ELSE 0 END AS contribution_margin
FROM sales_order_items i JOIN sales_orders o ON o.id=i.sales_order_id
WHERE o.status NOT IN ('DRAFT','PENDING_CONFIRMATION','CANCELLED','RETURNED')
GROUP BY i.product_id;

CREATE OR REPLACE VIEW customer_profitability_actual AS
SELECT o.customer_id,COUNT(*) AS order_count,COALESCE(SUM(o.sales),0) AS net_sales,
       COALESCE(SUM(o.contribution_profit),0) AS contribution_profit,
       CASE WHEN COALESCE(SUM(o.sales),0)>0 THEN SUM(o.contribution_profit)/SUM(o.sales) ELSE 0 END AS contribution_margin
FROM eyt_order_actual_profitability o GROUP BY o.customer_id;
