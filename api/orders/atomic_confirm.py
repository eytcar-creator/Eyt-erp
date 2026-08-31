from __future__ import annotations

from decimal import Decimal
from typing import Any


class AtomicOrderConfirmation:
    """Reference transaction boundary for production PostgreSQL integration.

    The same DB connection must be used for stock locks, reservation, order
    transition and audit. Any exception causes a rollback.
    """

    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def confirm(self, order_no: str) -> dict[str, Any]:
        with self.connection_factory() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT warehouse_code, status FROM sales_orders WHERE order_no=%s FOR UPDATE",
                        (order_no,),
                    )
                    order = cur.fetchone()
                    if not order:
                        raise KeyError(order_no)
                    if order[1] not in ("PENDING_CONFIRMATION", "CONFIRMED"):
                        raise ValueError("order is not confirmable")

                    cur.execute(
                        "SELECT product_id, quantity FROM sales_order_items WHERE order_no=%s ORDER BY id",
                        (order_no,),
                    )
                    items = cur.fetchall()
                    if not items:
                        raise ValueError("order has no items")

                    for product_id, quantity in items:
                        cur.execute(
                            """SELECT available_qty FROM inventory_stock
                               WHERE warehouse_code=%s AND product_id=%s FOR UPDATE""",
                            (order[0], product_id),
                        )
                        stock = cur.fetchone()
                        if not stock or Decimal(str(stock[0])) < Decimal(str(quantity)):
                            raise ValueError(f"insufficient stock: {product_id}")

                    for product_id, quantity in items:
                        cur.execute(
                            """UPDATE inventory_stock
                               SET available_qty=available_qty-%s,
                                   reserved_qty=reserved_qty+%s,
                                   updated_at=NOW()
                               WHERE warehouse_code=%s AND product_id=%s""",
                            (quantity, quantity, order[0], product_id),
                        )

                    cur.execute(
                        """UPDATE sales_orders SET status='RESERVED', confirmed_at=NOW(), updated_at=NOW()
                           WHERE order_no=%s""",
                        (order_no,),
                    )
                    cur.execute(
                        """INSERT INTO order_audit_log(order_no,event_type,created_at)
                           VALUES (%s,'ORDER_CONFIRMED_AND_RESERVED',NOW())""",
                        (order_no,),
                    )
                    conn.commit()
                    return {"order_no": order_no, "status": "RESERVED", "reserved": True}
            except Exception:
                conn.rollback()
                raise
