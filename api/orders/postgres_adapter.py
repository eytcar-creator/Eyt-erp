from __future__ import annotations

from decimal import Decimal
from typing import Any


class PostgresOrderRepository:
    """PostgreSQL adapter. Confirmation keeps credit, stock, cost, state and audit in one transaction."""

    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def create(self, order) -> dict[str, Any]:
        with self.connection_factory() as conn:
            try:
                with conn.cursor() as cur:
                    if order.idempotency_key:
                        cur.execute("SELECT order_no FROM sales_orders WHERE idempotency_key=%s", (order.idempotency_key,))
                        existing = cur.fetchone()
                        if existing:
                            return self.get(existing[0]) or {"order_no": existing[0]}
                    cur.execute("""
                        INSERT INTO sales_orders
                          (customer_id, representative_id, warehouse_code, channel, status,
                           idempotency_key, notes, payment_type, created_at)
                        VALUES (%s,%s,%s,%s,'PENDING_CONFIRMATION',%s,%s,%s,NOW())
                        RETURNING id, order_no, customer_id, representative_id, warehouse_code, channel, status, payment_type
                    """, (order.customer_id, order.representative_id, order.warehouse_code,
                          order.channel.value, order.idempotency_key, order.notes, order.payment_type.value))
                    row = cur.fetchone()
                    for line in order.items:
                        cur.execute("""
                            INSERT INTO sales_order_items
                              (sales_order_id, product_id, quantity, unit_price, unit_cost)
                            VALUES (%s,%s,%s,%s,0)
                        """, (row[0], line.product_id, Decimal(line.quantity), Decimal(line.unit_price)))
                    conn.commit()
                    return {"order_no": row[1], "customer_id": row[2], "representative_id": row[3],
                            "warehouse_code": row[4], "channel": row[5], "status": row[6], "payment_type": row[7]}
            except Exception:
                conn.rollback()
                raise

    def get(self, order_no: str) -> dict[str, Any] | None:
        with self.connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, order_no, customer_id, representative_id, warehouse_code, channel, status, payment_type
                    FROM sales_orders WHERE order_no=%s
                """, (order_no,))
                row = cur.fetchone()
                if not row:
                    return None
                cur.execute("""
                    SELECT product_id, quantity, unit_price
                    FROM sales_order_items WHERE sales_order_id=%s ORDER BY id
                """, (row[0],))
                items = [dict(product_id=r[0], quantity=r[1], unit_price=r[2]) for r in cur.fetchall()]
                return {"order_no": row[1], "customer_id": row[2], "representative_id": row[3],
                        "warehouse_code": row[4], "channel": row[5], "status": row[6],
                        "payment_type": row[7], "items": items}

    def confirm(self, order_no: str) -> dict[str, Any]:
        with self.connection_factory() as conn:
            try:
                with conn.cursor() as cur:
                    result = self.confirm_in_transaction(cur, order_no)
                    conn.commit()
                    return result
            except Exception:
                conn.rollback()
                raise

    def confirm_with_controls(self, order_no: str, customer_id: str, warehouse_code: str,
                              payment_type: str, items: tuple) -> dict[str, Any]:
        with self.connection_factory() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT order_no, customer_id, status, payment_type FROM sales_orders WHERE order_no=%s FOR UPDATE", (order_no,))
                    order_row = cur.fetchone()
                    if not order_row:
                        raise KeyError(order_no)
                    if order_row[2] not in ('PENDING_CONFIRMATION', 'CONFIRMED'):
                        raise ValueError("order is not confirmable")

                    if payment_type == 'CREDIT':
                        cur.execute("SELECT credit_limit, risk_level, manual_hold FROM customer_credit_profiles WHERE customer_id=%s FOR UPDATE", (customer_id,))
                        credit = cur.fetchone()
                        if not credit:
                            raise ValueError("credit profile not found")
                        cur.execute("SELECT COALESCE(SUM(outstanding),0) FROM receivables WHERE customer_id=%s", (customer_id,))
                        outstanding = Decimal(str(cur.fetchone()[0]))
                        cur.execute("SELECT COALESCE(SUM(outstanding),0) FROM receivables WHERE customer_id=%s AND days_overdue > 0", (customer_id,))
                        overdue = Decimal(str(cur.fetchone()[0]))
                        requested = sum((line.quantity * line.unit_price for line in items), Decimal('0'))
                        available = max(Decimal(str(credit[0])) - outstanding, Decimal('0'))
                        status = 'OK'
                        if credit[2] or credit[1] == 'BLOCKED': status = 'BLOCKED'
                        elif outstanding > Decimal(str(credit[0])): status = 'CREDIT_HOLD'
                        elif overdue > 0: status = 'REVIEW' if overdue < requested else 'HIGH_RISK'
                        allowed = status == 'OK' and available >= requested
                        reason = 'OK' if allowed else (status if status != 'OK' else 'CREDIT_LIMIT_EXCEEDED')
                        cur.execute("""
                            INSERT INTO order_credit_checks(order_no, customer_id, requested_amount, allowed, credit_status, available_credit, reason)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """, (order_no, customer_id, requested, allowed, status, available, reason))
                        if not allowed:
                            raise ValueError(f"credit check failed: {reason}")

                    PostgresInventoryGateway.reserve_in_transaction(cur, warehouse_code, items, order_no)
                    for line in items:
                        cur.execute("""
                            UPDATE sales_order_items i
                            SET cost_snapshot=COALESCE(p.purchase_price,0),
                                unit_cost=COALESCE(p.purchase_price,0),
                                contribution=i.quantity*(i.unit_price-COALESCE(p.purchase_price,0))
                            FROM products p
                            WHERE i.sales_order_id=(SELECT id FROM sales_orders WHERE order_no=%s)
                              AND i.product_id=%s AND i.product_id=p.id
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
            UPDATE sales_orders SET status='RESERVED', confirmed_at=NOW(), updated_at=NOW()
            WHERE order_no=%s AND status IN ('PENDING_CONFIRMATION','CONFIRMED')
            RETURNING order_no, status
        """, (order_no,))
        row = cur.fetchone()
        if not row:
            raise ValueError("order could not be confirmed")
        cur.execute("INSERT INTO order_audit_log(order_no,event_type,created_at) VALUES (%s,'ORDER_CONFIRMED_AND_RESERVED',NOW())", (order_no,))
        return {"order_no": row[0], "status": row[1], "reserved": True}


class PostgresInventoryGateway:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def reserve(self, warehouse_code: str, items) -> None:
        with self.connection_factory() as conn:
            try:
                with conn.cursor() as cur:
                    self.reserve_in_transaction(cur, warehouse_code, items, 'DIRECT')
                    conn.commit()
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def reserve_in_transaction(cur, warehouse_code: str, items, order_no: str) -> None:
        cur.execute("SELECT code FROM warehouses WHERE code=%s FOR UPDATE", (warehouse_code,))
        if not cur.fetchone():
            raise ValueError(f"warehouse not found: {warehouse_code}")
        for line in items:
            cur.execute("""
                SELECT COALESCE(SUM(CASE
                    WHEN transaction_type IN ('RECEIPT','PRODUCTION_RECEIPT','TRANSFER_IN','RETURN') THEN quantity
                    WHEN transaction_type IN ('ISSUE','TRANSFER_OUT','CONSUMPTION','SCRAP') THEN -quantity
                    ELSE 0 END),0)
                FROM inventory_transactions
                WHERE warehouse_code=%s AND product_code=(SELECT product_code FROM products WHERE id=%s)
            """, (warehouse_code, line.product_id))
            physical = Decimal(str(cur.fetchone()[0]))
            cur.execute("""
                SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations
                WHERE warehouse_code=%s AND product_code=(SELECT product_code FROM products WHERE id=%s) AND status='RESERVED'
            """, (warehouse_code, line.product_id))
            reserved = Decimal(str(cur.fetchone()[0]))
            if physical - reserved < line.quantity:
                raise ValueError(f"insufficient stock: {line.product_id}")
            cur.execute("""
                INSERT INTO inventory_reservations
                  (document_no,warehouse_code,product_code,quantity,status,reference_type,reference_id,created_at)
                VALUES (%s,%s,(SELECT product_code FROM products WHERE id=%s),%s,'RESERVED','SALES_ORDER',%s,NOW())
            """, (order_no, warehouse_code, line.product_id, line.quantity, order_no))
