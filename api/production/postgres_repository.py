"""PostgreSQL persistence adapter for E.Y.T production orders."""
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

    def start_operation(self, order_no: str, sequence_no: int,
                        operation_code: str, operation_name: str,
                        contractor_name: str | None = None) -> None:
        with self.connection.cursor() as cur:
            cur.execute("SELECT id FROM production_orders WHERE order_no=%s", (order_no,))
            order = cur.fetchone()
            if order is None:
                raise KeyError(f"Production order not found: {order_no}")
            cur.execute(
                """SELECT id FROM production_operations
                   WHERE production_order_id=%s AND operation_code=%s
                     AND status='in_progress'""",
                (order[0], operation_code),
            )
            if cur.fetchone() is not None:
                raise ValueError(f"Operation already in progress: {operation_code}")
            cur.execute(
                """INSERT INTO production_operations
                   (production_order_id, sequence_no, operation_code,
                    operation_name, contractor_name, input_qty, accepted_qty,
                    rejected_qty, waste_qty, service_cost, transport_cost,
                    actual_start, status)
                   VALUES (%s,%s,%s,%s,%s,0,0,0,0,0,0,
                           CURRENT_TIMESTAMP,'in_progress')""",
                (order[0], sequence_no, operation_code, operation_name,
                 contractor_name),
            )
            cur.execute(
                "UPDATE production_orders SET status='in_progress', actual_start=COALESCE(actual_start, CURRENT_TIMESTAMP) WHERE id=%s",
                (order[0],),
            )
        self.connection.commit()

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
                """SELECT id FROM production_operations
                   WHERE production_order_id=%s AND operation_code=%s
                     AND status='in_progress'
                   ORDER BY id DESC LIMIT 1""",
                (order[0], operation_code),
            )
            operation = cur.fetchone()
            if operation is None:
                raise ValueError(f"Operation must be started before completion: {operation_code}")
            cur.execute(
                """UPDATE production_operations
                   SET sequence_no=%s, operation_name=%s, contractor_name=%s,
                       input_qty=%s, accepted_qty=%s, rejected_qty=%s,
                       waste_qty=%s, service_cost=%s, transport_cost=%s,
                       actual_end=CURRENT_TIMESTAMP, status='completed'
                   WHERE id=%s""",
                (sequence_no, operation_name, contractor_name, input_qty,
                 accepted_qty, rejected_qty, waste_qty, service_cost,
                 transport_cost, operation[0]),
            )
        self.connection.commit()
