import os
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest


@pytest.mark.integration
def test_ario_2000_end_to_end_profit_flow():
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not configured")

    suffix = uuid4().hex[:10]
    sku = f"TEST-ARIO-2000-{suffix}"
    component_skus = {
        "BODY": f"TEST-ARIO-BODY-{suffix}",
        "NUT": f"TEST-ARIO-NUT-{suffix}",
        "GREASE": f"TEST-ARIO-GREASE-{suffix}",
        "PIN": f"TEST-ARIO-PIN-{suffix}",
        "BOOT": f"TEST-ARIO-BOOT-{suffix}",
        "SPRING": f"TEST-ARIO-SPRING-{suffix}",
        "RUBBER": f"TEST-ARIO-RUBBER-{suffix}",
        "WASHER": f"TEST-ARIO-WASHER-{suffix}",
        "PACK": f"TEST-ARIO-PACK-{suffix}",
    }
    component_costs = {
        "BODY": Decimal("135000"),
        "NUT": Decimal("4000"),
        "GREASE": Decimal("5000"),
        "PIN": Decimal("40000"),
        "BOOT": Decimal("12000"),
        "SPRING": Decimal("5000"),
        "RUBBER": Decimal("15000"),
        "WASHER": Decimal("5000"),
        "PACK": Decimal("10000"),
    }
    order_no = f"MO-ARIO-2000-{suffix}"
    sales_order_no = f"SO-ARIO-2000-{suffix}"

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            # Product Master + legacy product bridge.
            for name, component_sku in {"FG": sku, **component_skus}.items():
                cost = Decimal("0") if name == "FG" else component_costs[name]
                cur.execute(
                    """
                    INSERT INTO eyt_product_master
                      (sku,code128,product_name_fa,product_type,category,brand,unit,status,
                       standard_cost,last_cost,retail_price)
                    VALUES (%s,%s,%s,%s,%s,'E.Y.T','PCS','ACTIVE',%s,%s,%s)
                    ON CONFLICT (sku) DO NOTHING
                    """,
                    (component_sku, f"9{suffix}-{name}",
                     f"Test Ario {name}", "FINISHED_GOOD", "TEST",
                     cost, cost, Decimal("700000") if name == "FG" else cost),
                )
                cur.execute(
                    """
                    INSERT INTO products(sku,product_code,name_fa,product_type,brand,unit,purchase_price,sale_price)
                    VALUES (%s,%s,%s,'FINISHED_GOOD','E.Y.T','PCS',%s,%s)
                    ON CONFLICT (sku) DO NOTHING
                    """,
                    (component_sku, component_sku, f"Test Ario {name}", cost,
                     Decimal("700000") if name == "FG" else cost),
                )

            cur.execute("SELECT id FROM eyt_product_master WHERE sku=%s", (sku,))
            product_id = cur.fetchone()[0]

            # Active BOM using the user's known Ario material/component structure.
            cur.execute(
                """
                INSERT INTO eyt_bom(product_id,bom_code,version,status,yield_factor)
                VALUES (%s,%s,1,'ACTIVE',1)
                RETURNING id
                """,
                (product_id, f"BOM-{suffix}"),
            )
            bom_id = cur.fetchone()[0]
            quantities = {"BODY": 1, "NUT": 1, "GREASE": 1, "PIN": 1, "BOOT": 1,
                          "SPRING": 1, "RUBBER": 1, "WASHER": 1, "PACK": 1}
            for seq, (name, qty) in enumerate(quantities.items(), 10):
                cur.execute(
                    """
                    INSERT INTO eyt_bom_item(bom_id,component_product_id,quantity_per,sequence_no)
                    SELECT %s,id,%s,%s FROM eyt_product_master WHERE sku=%s
                    """,
                    (bom_id, qty, seq, component_skus[name]),
                )

            # Routing mirrors the EYT reference route and known unit service costs.
            cur.execute(
                """
                INSERT INTO eyt_routing(product_id,routing_code,version,status)
                VALUES (%s,%s,1,'ACTIVE') RETURNING id
                """,
                (product_id, f"RT-{suffix}"),
            )
            routing_id = cur.fetchone()[0]
            operations = [
                ("FORGE", 7, 120000),
                ("DRILL", 1, 14000),
                ("CNC", 7, 30000),
                ("TAP", 5, 0),
                ("BLACK_PLATE", 6, 40000),
                ("FINAL_QC", 1, 100000),
            ]
            for seq, (code, days, unit_cost) in enumerate(operations, 10):
                cur.execute(
                    """
                    INSERT INTO eyt_routing_operation
                      (routing_id,sequence_no,operation_code,operation_name_fa,
                       make_or_buy,planned_days,capacity_per_day,unit_cost,qc_required)
                    VALUES (%s,%s,%s,%s,'MAKE',%s,300,%s,%s)
                    """,
                    (routing_id, seq, code, code, days, unit_cost, code == "FINAL_QC"),
                )

            # 2,000-unit production order.
            cur.execute(
                """
                INSERT INTO production_orders
                  (order_no,product_code,product_name,target_qty,order_date,status,product_master_id)
                VALUES (%s,%s,%s,2000,CURRENT_DATE,'completed',%s)
                RETURNING id
                """,
                (order_no, sku, "Test Ario Steering Ball Joint", product_id),
            )
            production_id = cur.fetchone()[0]

            # Operation actuals: 2,000 accepted.
            for seq, (code, _, service_cost) in enumerate(operations, 1):
                cur.execute(
                    """
                    INSERT INTO production_operations
                      (production_order_id,sequence_no,operation_code,operation_name,
                       input_qty,accepted_qty,rejected_qty,waste_qty,service_cost,status)
                    VALUES (%s,%s,%s,%s,2000,2000,0,0,%s,'completed')
                    """,
                    (production_id, seq, code, code, Decimal(service_cost) * 2000),
                )

            # Material receipts and actual consumption at the known costs.
            for name, component_sku in component_skus.items():
                cost = component_costs[name]
                cur.execute(
                    """
                    INSERT INTO inventory_transactions
                      (product_code,warehouse_code,quantity,unit,transaction_type,
                       reference_type,reference_id,unit_cost)
                    VALUES (%s,'MAIN',2000,'PCS','RECEIPT','TEST',%s,%s)
                    """,
                    (component_sku, order_no, cost),
                )
                cur.execute(
                    """
                    INSERT INTO inventory_transactions
                      (document_no,warehouse_code,product_code,quantity,unit,transaction_type,
                       reference_type,reference_id,unit_cost)
                    VALUES (%s,'MAIN',2000,'PCS','CONSUMPTION','PRODUCTION',%s,%s)
                    """,
                    (f"CONS-{name}-{suffix}", order_no, cost),
                )
                cur.execute(
                    """
                    INSERT INTO production_material_movements
                      (production_order_id,material_code,warehouse_code,quantity,movement_type,
                       document_no,actor_name,component_product_id,unit_cost,quantity_source)
                    SELECT %s,%s,'MAIN',2000,'ISSUE',%s,'integration-test',id,%s,'ACTUAL'
                    FROM eyt_product_master WHERE sku=%s
                    """,
                    (production_id, component_sku, f"PMM-{name}-{suffix}", cost, component_sku),
                )

            # Known extra scrap cost from the production record.
            cur.execute(
                """
                INSERT INTO production_costs(production_order_id,cost_type,description,amount)
                VALUES (%s,'SCRAP','Ario test scrap',%s)
                """,
                (production_id, Decimal("10000") * 2000),
            )

            # QC: all 2,000 accepted.
            cur.execute(
                """
                INSERT INTO quality_inspections
                  (production_order_id,inspected_qty,accepted_qty,rejected_qty,result,inspector_name)
                VALUES (%s,2000,2000,0,'PASS','integration-test')
                """,
                (production_id,),
            )

            cur.execute("SELECT eyt_snapshot_actual_production_cost(%s)", (production_id,))
            snapshot_id = cur.fetchone()[0]
            assert snapshot_id is not None

            cur.execute(
                """
                SELECT cost_per_unit,total_cost,material_cost,operation_cost,scrap_cost
                FROM eyt_production_cost_snapshot WHERE id=%s
                """,
                (snapshot_id,),
            )
            cost_per_unit, total_cost, material_cost, operation_cost, scrap_cost = cur.fetchone()
            assert material_cost == Decimal("462000000")
            assert operation_cost == Decimal("608000000")
            assert scrap_cost == Decimal("20000000")
            assert cost_per_unit == Decimal("545000")
            assert total_cost == Decimal("1090000000")

            # Customer + sales order + invoice + full collection.
            cur.execute(
                """
                INSERT INTO customers(customer_code,name)
                VALUES (%s,'EYT Ario Integration Customer')
                RETURNING id
                """,
                (f"CUST-{suffix}",),
            )
            customer_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO sales_orders(order_no,customer_id,warehouse_code,order_date,status,subtotal,total_amount)
                VALUES (%s,%s,'MAIN',CURRENT_DATE,'FULFILLED',1400000000,1400000000)
                RETURNING id
                """,
                (sales_order_no, customer_id),
            )
            sales_order_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO sales_order_items(sales_order_id,product_id,quantity,unit_price,unit_cost)
                SELECT %s,id,2000,700000,545000 FROM products WHERE sku=%s
                RETURNING id
                """,
                (sales_order_id, sku),
            )
            order_item_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO invoices(invoice_no,sales_order_id,customer_id,subtotal,receivable_amount)
                VALUES (%s,%s,%s,1400000000,1400000000)
                RETURNING id
                """,
                (f"INV-{suffix}", sales_order_id, customer_id),
            )
            invoice_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO payments(customer_id,amount,payment_method,reference_no)
                VALUES (%s,1400000000,'BANK','PAY-%s')
                RETURNING id
                """,
                (customer_id, suffix),
            )
            payment_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO payment_allocations(payment_id,invoice_id,amount) VALUES (%s,%s,1400000000)",
                (payment_id, invoice_id),
            )

            # Bridge actual production cost to the sold line.
            cur.execute(
                "SELECT eyt_apply_actual_production_cost_to_order_line(%s,%s,%s)",
                (sales_order_no, order_item_id, production_id),
            )
            applied_cost = cur.fetchone()[0]
            assert applied_cost == Decimal("545000")

            cur.execute(
                """
                SELECT sales,actual_cogs,contribution_profit,contribution_margin
                FROM eyt_order_actual_profitability WHERE order_no=%s
                """,
                (sales_order_no,),
            )
            sales, actual_cogs, contribution_profit, contribution_margin = cur.fetchone()
            assert sales == Decimal("1400000000")
            assert actual_cogs == Decimal("1090000000")
            assert contribution_profit == Decimal("310000000")
            assert contribution_margin == Decimal("0.2214285714285714285714285714")

            # Collection control: the invoice is fully allocated.
            cur.execute(
                """
                SELECT i.receivable_amount - COALESCE(SUM(pa.amount),0)
                FROM invoices i LEFT JOIN payment_allocations pa ON pa.invoice_id=i.id
                WHERE i.id=%s GROUP BY i.id,i.receivable_amount
                """,
                (invoice_id,),
            )
            outstanding = cur.fetchone()[0]
            assert outstanding == Decimal("0")

            # Sanity: all 2,000 units passed QC and material variance is zero.
            cur.execute(
                """
                SELECT accepted_qty,rejected_qty FROM quality_inspections
                WHERE production_order_id=%s
                """,
                (production_id,),
            )
            assert cur.fetchone() == (Decimal("2000"), Decimal("0"))

            cur.execute(
                """
                SELECT COALESCE(SUM(quantity),0) FROM production_material_movements
                WHERE production_order_id=%s AND movement_type='ISSUE'
                """,
                (production_id,),
            )
            assert cur.fetchone()[0] == Decimal("18000")
