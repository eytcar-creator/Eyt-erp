from __future__ import annotations

from decimal import Decimal
from typing import Any


class PostgresOrderRepository:
    """SQL adapter with a single transaction boundary for order confirmation."""

    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def create(self, order) -> dict[str, Any]:
        with self.connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sales_orders
                      (customer_id, representative_id, warehouse_code, channel,
                       status, idempotency_key, notes, payment_type, created_at)
                    VALUES (%s,%s,%s,%s,'PENDING_CONFIRMATION',%s,%s,%s,NOW())
                    RETURNING order_no, customer_id, representative_id,
                              warehouse_code, channel, status, payment_type
                """, (order.customer_id, order.representative_id,
                       order.warehouse_code, order.channel.value,
                       order.idempotency_key, order.notes,
                       order.payment_type.value))
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
                        "channel": row[4], "status": row[5],
                        "payment_type": row[6]}

    def get(self, order_no: str) -> dict[str, Any] | None:
        with self.connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT order_no, customer_id, representative_id,
                           warehouse_code, channel, status, payment_type
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
                        "channel": row[4], "status": row[5],
                        "payment_type": row[6], "items": items}

    def confirm(self, order_no: str) -> dict[str, Any]:
        with self.connection_factory() as conn:
            with conn.cursor() as cur:
                result = self.confirm_in_transaction(cur, order_no)
                conn.commit()
                return result

    def confirm_with_controls(self, order_no: str, customer_id: str,
                              warehouse_code: str, payment_type: str,
                              items: tuple) -> dict[str, Any]:
        """Credit gate + stock reservation + cost snapshot + state/audit atomically."""
        with self.connection_factory() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT order_no, customer_id, status, payment_type
                        FROM sales_orders
                        WHERE order_no=%s
                        FOR UPDATE
                    """, (order_no,))
                    order_row = cur.fetchone()
                    if not order_row:
                        raise KeyError(order_no)
                    if order_row[2] not in ('PENDING_CONFIRMATION','CONFIRMED'):
                        raise ValueError("order is not confirmable")

                    if payment_type == 'CREDIT':
                        cur.execute("""
                            SELECT credit_limit, risk_level, manual_hold
                            FROM customer_credit_profiles
                            WHERE customer_id=%s
                            FOR UPDATE
                        """, (customer_id,))
                        credit = cur.fetchone()
                        if not credit:
                            raise ValueError("credit profile not found")
                        cur.execute("""
                            SELECT COALESCE(SUM(outstanding),0)
                            FROM receivables WHERE customer_id=%s
                        """, (customer_id,))
                        outstanding = Decimal(str(cur.fetchone()[0]))
                        credit_limit = Decimal(str(credit[0]))
                        overdue = Decimal('0')
                        cur.execute("""
                            SELECT COALESCE(SUM(outstanding),0)
                            FROM receivables
                            WHERE customer_id=%s AND days_overdue > 0
                        """, (customer_id,))
                        overdue = Decimal(str(cur.fetchone()[0]))
                        requested = sum((line.quantity * line.unit_price for line in items), Decimal('0'))
                        available = max(credit_limit - outstanding, Decimal('0'))
                        status = 'OK'
                        if credit[2] or credit[1] == 'BLOCKED':
                            status = 'BLOCKED'
                        elif outstanding > credit_limit:
                            status = 'CREDIT_HOLD'
                        elif any(Decimal(str(x)) > 0 for x in [overdue]) and overdue > 0:
                            status = 'REVIEW' if overdue < requested else 'HIGH_RISK'
                        allowed = status == 'OK' and available >= requested
                        reason = 'OK' if allowed else (status if status != 'OK' else 'CREDIT_LIMIT_EXCEEDED')
                        cur.execute("""
                            INSERT INTO order_credit_checks
                              (order_no, customer_id, requested_amount, allowed,
                               credit_status, available_credit, reason)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """, (order_no, customer_id, requested, allowed,
                               status, available, reason))
                        if not allowed:
                            raise ValueError(f"credit check failed: {reason}")

                    PostgresInventoryGateway.reserve_in_transaction(cur, warehouse_code, items)

                    for line in items:
                        cur.execute("""
                            UPDATE sales_order_items i
                            SET cost_snapshot = COALESCE(i.cost_snapshot, p.standard_cost, 0),
                                contribution = i.quantity * (i.unit_price - COALESCE(i.cost_snapshot, p.standard_cost, 0))
                            FROM products p
                            WHERE i.order_no=%s AND i.product_id=%s
                              AND i.product_id=p.product_uuid
                              AND i.cost_snapshot IS NULL
                        """, (order_no, line.product_id))

                    result = self.confirm_in_transaction(cur, order_no)
                    conn.commit()
                    return result
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def confirm_in_transaction(cur, order_no: str) -> dict[str, Any]:
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
        with self.connection_factory() as conn:
            with conn.cursor() as cur:
                self.reserve_in_transaction(cur, warehouse_code, items)
                conn.commit()

    @staticmethod
    def reserve_in_transaction(cur, warehouse_code: str, items) -> None:
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
