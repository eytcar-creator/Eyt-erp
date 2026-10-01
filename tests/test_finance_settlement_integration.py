import os
from datetime import datetime, timedelta

import pytest

pytestmark = pytest.mark.integration


def _connect():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not configured")
    psycopg = pytest.importorskip("psycopg")
    return psycopg.connect(database_url)


def test_finance_settlement_alert_and_notification_flow():
    with _connect() as conn:
        with conn.cursor() as cur:
            customer_id = cur.execute(
                """
                INSERT INTO customers(customer_code,name)
                VALUES(%s,%s)
                RETURNING id
                """,
                ("CI-FINANCE-001", "CI Finance Customer"),
            ).fetchone()[0]

            product_id = cur.execute(
                """
                INSERT INTO products(sku,product_code,name_fa,purchase_price,sale_price)
                VALUES(%s,%s,%s,%s,%s)
                RETURNING id
                """,
                ("CI-FINANCE-SKU", "CI-FINANCE-PRODUCT", "CI Finance Product", 10, 100),
            ).fetchone()[0]

            order_id = cur.execute(
                """
                INSERT INTO sales_orders(
                    order_no,customer_id,warehouse_code,subtotal,status
                )
                VALUES(%s,%s,'MAIN',%s,'CONFIRMED')
                RETURNING id
                """,
                ("CI-FINANCE-ORDER-001", customer_id, 1000),
            ).fetchone()[0]

            cur.execute(
                """
                INSERT INTO sales_order_items(
                    sales_order_id,product_id,quantity,unit_price,unit_cost
                )
                VALUES(%s,%s,10,100,10)
                """,
                (order_id, product_id),
            )

            invoice_id = cur.execute(
                """
                INSERT INTO invoices(
                    invoice_no,sales_order_id,customer_id,subtotal,
                    receivable_amount,status,due_at
                )
                VALUES(%s,%s,%s,1000,1000,'ISSUED',%s)
                RETURNING id
                """,
                (
                    "CI-FINANCE-INV-001",
                    order_id,
                    customer_id,
                    datetime.utcnow() + timedelta(hours=12),
                ),
            ).fetchone()[0]

            conn.commit()

    try:
        from api.production.finance_alert_sync_service import sync_settlement_alerts
        from api.production.finance_notification_result import mark_sent
        from api.production.finance_notification_worker_contract import claim_batch

        first = sync_settlement_alerts()
        assert first["created"] == 1

        with _connect() as conn:
            with conn.cursor() as cur:
                alert = cur.execute(
                    """
                    SELECT alert_type,status,outstanding_amount
                    FROM finance_settlement_alerts
                    WHERE entity_type='CUSTOMER_INVOICE' AND entity_id=%s
                    """,
                    (str(invoice_id),),
                ).fetchone()
                assert alert == ("DUE_24H", "OPEN", 1000)

                outbox = cur.execute(
                    """
                    SELECT id,status,event_type,entity_id
                    FROM finance_notification_outbox
                    WHERE entity_type='CUSTOMER_INVOICE' AND entity_id=%s
                    ORDER BY id DESC LIMIT 1
                    """,
                    (str(invoice_id),),
                ).fetchone()
                assert outbox[1:] == ("PENDING", "FINANCE_SETTLEMENT_ALERT", str(invoice_id))
                event_id = outbox[0]

        second = sync_settlement_alerts()
        assert second["created"] == 0

        claimed = claim_batch("ci-finance-worker", limit=10)
        matching = [event for event in claimed if event.id == event_id]
        assert len(matching) == 1
        assert matching[0].entity_id == str(invoice_id)
        assert mark_sent(event_id, "ci-finance-worker") is True

        with _connect() as conn:
            with conn.cursor() as cur:
                status = cur.execute(
                    "SELECT status FROM finance_notification_outbox WHERE id=%s",
                    (event_id,),
                ).fetchone()[0]
                assert status == "SENT"
                cur.execute(
                    "SELECT status FROM finance_settlement_alerts WHERE entity_id=%s",
                    (str(invoice_id),),
                )
                assert cur.fetchone()[0] == "OPEN"
                conn.commit()
    finally:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM finance_notification_outbox WHERE entity_type='CUSTOMER_INVOICE' AND entity_id=%s",
                    (str(invoice_id),),
                )
                cur.execute(
                    "DELETE FROM finance_settlement_alerts WHERE entity_type='CUSTOMER_INVOICE' AND entity_id=%s",
                    (str(invoice_id),),
                )
                cur.execute("DELETE FROM invoices WHERE id=%s", (invoice_id,))
                cur.execute("DELETE FROM sales_order_items WHERE sales_order_id=%s", (order_id,))
                cur.execute("DELETE FROM sales_orders WHERE id=%s", (order_id,))
                cur.execute("DELETE FROM purchase_history WHERE product_id=%s", (product_id,))
                cur.execute("DELETE FROM products WHERE id=%s", (product_id,))
                cur.execute("DELETE FROM customers WHERE id=%s", (customer_id,))
                conn.commit()
