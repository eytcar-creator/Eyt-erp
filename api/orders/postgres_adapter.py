from __future__ import annotations

from decimal import Decimal
from typing import Any


class PostgresOrderRepository:
    """SQL adapter contract for the E.Y.T Order Center.

    The caller supplies a DB connection/transaction factory. SQL is kept here so
    HTTP handlers never manipulate persistence directly.
    """

    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def create(self, order) -> dict[str, Any]:
        with self.connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sales_orders
                      (customer_id, representative_id, warehouse_code, channel,
                       status, idempotency_key, notes, created_at)
                    VALUES (%s,%s,%s,%s,'PENDING_CONFIRMATION',%s,%s,NOW())
                    RETURNING order_no, customer_id, representative_id,
                              warehouse_code, channel, status
                """, (order.customer_id, order.representative_id,
                       order.warehouse_code, order.channel.value,
                       order.idempotency_key, order.notes))
                row = cur.fetchone()
                if not row:
                    raise RuntimeError("order creation failed")
                order_no = row[0]
                for line in order.items:
                    cur.execute("""
                        INSERT INTO sales_order_items
                          (order_no, product_id, quantity, unit_price)
                        VALUES (%s,%s,%s,%s)
                    """, (order_no, line.product_id,
                           Decimal(line.quantity), Decimal(line.unit_price)))
                conn.commit()
                return {"order_no": row[0], "customer_id": row[1],
                        "representative_id": row[2], "warehouse_code": row[3],
                        "channel": row[4], "status": row[5]}

    def get(self, order_no: str) -> dict[str, Any] | None:
        with self.connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT order_no, customer_id, representative_id,
                           warehouse_code, channel, status
                    FROM sales_orders WHERE order_no=%s
                """, (order_no,))
                row = cur.fetchone()
                if not row:
                    return None
                cur.execute("""
                    SELECT product_id, quantity, unit_price
                    FROM sales_order_items WHERE order_no=%s
                    ORDER BY id
                """, (order_no,))
                items = [dict(product_id=r[0], quantity=r[1], unit_price=r[2])
                         for r in cur.fetchall()]
                return {"order_no": row[0], "customer_id": row[1],
                        "representative_id": row[2], "warehouse_code": row[3],
                        "channel": row[4], "status": row[5], "items": items}

    def confirm(self, order_no: str) -> dict[str, Any]:
        """Confirm and reserve in the caller-owned transaction boundary."""
        with self.connection_factory() as conn:
            with conn.cursor() as cur:
                self.confirm_in_transaction(cur, order_no)
                conn.commit()
                return {"order_no": order_no, "status": "RESERVED", "reserved": True}

    @staticmethod
    def confirm_in_transaction(cur, order_no: str) -> dict[str, Any]:
        """Change order state and audit within an existing transaction."""
        cur.execute("""
            UPDATE sales_orders
            SET status='RESERVED', confirmed_at=NOW(), updated_at=NOW()
            WHERE order_no=%s AND status IN ('PENDING_CONFIRMATION','CONFIRMED')
            RETURNING order_no, status
        """, (order_no,))
        row = cur.fetchone()
        if not row:
            raise ValueError("order could not be confirmed")
        cur.execute("""
            INSERT INTO order_audit_log(order_no, event_type, created_at)
            VALUES (%s,'ORDER_CONFIRMED_AND_RESERVED',NOW())
        """, (order_no,))
        return {"order_no": row[0], "status": row[1], "reserved": True}


class PostgresInventoryGateway:
    """Inventory reservation adapter using row locks for concurrency safety."""

    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def reserve(self, warehouse_code: str, items) -> None:
        """Legacy standalone reservation path. Prefer reserve_in_transaction."""
        with self.connection_factory() as conn:
            with conn.cursor() as cur:
                self.reserve_in_transaction(cur, warehouse_code, items)
                conn.commit()

    @staticmethod
    def reserve_in_transaction(cur, warehouse_code: str, items) -> None:
        """Reserve inventory using the same DB transaction as order confirmation."""
        for line in items:
            cur.execute("""
                SELECT available_qty FROM inventory_stock
                WHERE warehouse_code=%s AND product_id=%s
                FOR UPDATE
            """, (warehouse_code, line.product_id))
            row = cur.fetchone()
            if not row or Decimal(str(row[0])) < line.quantity:
                raise ValueError(f"insufficient stock: {line.product_id}")
            cur.execute("""
                UPDATE inventory_stock
                SET available_qty=available_qty-%s,
                    reserved_qty=reserved_qty+%s,
                    updated_at=NOW()
                WHERE warehouse_code=%s AND product_id=%s
            """, (line.quantity, line.quantity, warehouse_code, line.product_id))
