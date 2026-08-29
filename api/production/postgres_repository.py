"""PostgreSQL persistence adapter for E.Y.T production orders.

Requires psycopg (v3). SQL is parameterized; transaction ownership stays with
this adapter so API handlers can remain focused on business behavior.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


class PostgresProductionRepository:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def create_order(self, order_no: str, product_code: str, product_name: str,
                     target_qty: Decimal, order_date: str,
                     customer_id: int | None = None) -> None:
        with self.connection.cursor() as cur:
            cur.execute(
                """INSERT INTO production_orders
                   (order_no, product_code, product_name, target_qty,
                    order_date, customer_id, status)
                   VALUES (%s, %s, %s, %s, %s, %s, 'planned')""",
                (order_no, product_code, product_name, target_qty,
                 order_date, customer_id),
            )
        self.connection.commit()

    def get_order(self, order_no: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cur:
            cur.execute(
                """SELECT id, order_no, product_code, product_name,
                          target_qty, order_date, planned_start, planned_end,
                          actual_start, actual_end, status, customer_id
                   FROM production_orders WHERE order_no = %s""",
                (order_no,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            columns = [d.name for d in cur.description]
            return dict(zip(columns, row))

    def record_operation(self, order_no: str, sequence_no: int,
                         operation_code: str, operation_name: str,
                         input_qty: Decimal, accepted_qty: Decimal,
                         rejected_qty: Decimal, waste_qty: Decimal,
                         service_cost: Decimal = Decimal("0"),
                         transport_cost: Decimal = Decimal("0"),
                         contractor_name: str | None = None) -> None:
        with self.connection.cursor() as cur:
            cur.execute("SELECT id FROM production_orders WHERE order_no=%s", (order_no,))
            order = cur.fetchone()
            if order is None:
                raise KeyError(f"Production order not found: {order_no}")
            cur.execute(
                """INSERT INTO production_operations
                   (production_order_id, sequence_no, operation_code,
                    operation_name, contractor_name, input_qty, accepted_qty,
                    rejected_qty, waste_qty, service_cost, transport_cost,
                    actual_start, actual_end, status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                           CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'completed')""",
                (order[0], sequence_no, operation_code, operation_name,
                 contractor_name, input_qty, accepted_qty, rejected_qty,
                 waste_qty, service_cost, transport_cost),
            )
        self.connection.commit()
