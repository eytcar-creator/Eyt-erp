from __future__ import annotations

import os
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/cash-collection", tags=["Cash Collection"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


class InvoiceIn(BaseModel):
    order_no: str
    prepayment_amount: Decimal = Field(default=Decimal("0"), ge=0)


class PaymentIn(BaseModel):
    invoice_id: str
    amount: Decimal = Field(gt=0)
    payment_method: Optional[str] = None
    reference_no: Optional[str] = None
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None


@router.get("/invoices")
def invoices(customer_id: Optional[str] = None, status: Optional[str] = None, limit: int = Query(200, ge=1, le=1000)):
    with _connect() as conn, conn.cursor() as cur:
        sql = "SELECT invoice_id, invoice_no, sales_order_id, customer_id, invoice_date, subtotal, prepayment_amount, receivable_amount, collected, outstanding, collection_status FROM cash_collection_control WHERE 1=1"
        params = []
        if customer_id:
            sql += " AND customer_id=%s"
            params.append(customer_id)
        if status:
            sql += " AND collection_status=%s"
            params.append(status)
        sql += " ORDER BY invoice_date DESC LIMIT %s"
        params.append(limit)
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [
        {"invoiceId": str(r[0]), "invoiceNo": r[1], "salesOrderId": str(r[2]), "customerId": str(r[3]),
         "invoiceDate": r[4], "subtotal": r[5], "prepayment": r[6], "receivable": r[7],
         "collected": r[8], "outstanding": r[9], "status": r[10]}
        for r in rows
    ]


@router.post("/invoice", status_code=201)
def create_invoice(payload: InvoiceIn):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT so.id, so.customer_id, so.status, so.subtotal,
                   COALESCE(so.prepayment_amount, 0),
                   EXISTS(SELECT 1 FROM invoices i WHERE i.sales_order_id=so.id)
            FROM sales_orders so
            WHERE so.order_no=%s
            FOR UPDATE
        """, (payload.order_no,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(404, "Sales order not found")
        order_id, customer_id, status, subtotal, existing_prepayment, exists = order
        if exists:
            cur.execute("SELECT id, invoice_no FROM invoices WHERE sales_order_id=%s", (order_id,))
            existing = cur.fetchone()
            return {"invoiceId": str(existing[0]), "invoiceNo": existing[1], "existing": True}
        if status not in {"CONFIRMED", "RESERVED", "PREPARING", "READY_TO_SHIP", "SHIPPED", "DELIVERED"}:
            raise HTTPException(409, "order must be confirmed before invoicing")
        prepayment = payload.prepayment_amount
        if prepayment > subtotal:
            raise HTTPException(422, "prepayment exceeds order subtotal")
        cur.execute("SELECT COALESCE(MAX(invoice_no), '') FROM invoices WHERE invoice_no LIKE 'EYT-INV-%'")
        last = cur.fetchone()[0]
        try:
            seq = int(last.rsplit('-', 1)[-1]) + 1 if last else 1
        except ValueError:
            seq = 1
        invoice_no = f"EYT-INV-{seq:08d}"
        cur.execute("""
            INSERT INTO invoices(invoice_no, sales_order_id, customer_id, subtotal,
                                  prepayment_amount, receivable_amount, source_type, source_id)
            VALUES(%s,%s,%s,%s,%s,%s,'SALES_ORDER',%s)
            RETURNING id
        """, (invoice_no, order_id, customer_id, subtotal, prepayment, subtotal-prepayment, order_id))
        invoice_id = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO invoice_items(invoice_id, product_id, quantity, unit_price, unit_cost)
            SELECT %s, product_id, quantity, unit_price, unit_cost
            FROM sales_order_items WHERE sales_order_id=%s
        """, (invoice_id, order_id))
        conn.commit()
    return {"invoiceId": str(invoice_id), "invoiceNo": invoice_no, "existing": False}


@router.post("/payment", status_code=201)
def record_payment(payload: PaymentIn):
    with _connect() as conn, conn.cursor() as cur:
        if payload.idempotency_key:
            cur.execute("SELECT id FROM payments WHERE idempotency_key=%s", (payload.idempotency_key,))
            existing = cur.fetchone()
            if existing:
                return {"paymentId": str(existing[0]), "existing": True}
        cur.execute("""
            SELECT customer_id, receivable_amount,
                   COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE invoice_id=i.id),0)
            FROM invoices i WHERE i.id=%s AND i.status <> 'VOID' FOR UPDATE
        """, (payload.invoice_id,))
        inv = cur.fetchone()
        if not inv:
            raise HTTPException(404, "Invoice not found")
        customer_id, receivable, collected = inv
        outstanding = receivable - collected
        if payload.amount > outstanding:
            raise HTTPException(422, f"payment exceeds outstanding balance: {outstanding}")
        cur.execute("""
            INSERT INTO payments(customer_id, amount, payment_method, reference_no, notes, idempotency_key)
            VALUES(%s,%s,%s,%s,%s,%s) RETURNING id
        """, (customer_id, payload.amount, payload.payment_method, payload.reference_no, payload.notes, payload.idempotency_key))
        payment_id = cur.fetchone()[0]
        cur.execute("INSERT INTO payment_allocations(payment_id, invoice_id, amount) VALUES(%s,%s,%s)",
                    (payment_id, payload.invoice_id, payload.amount))
        new_collected = collected + payload.amount
        new_status = 'PAID' if new_collected >= receivable else 'PARTIALLY_PAID'
        cur.execute("UPDATE invoices SET status=%s WHERE id=%s", (new_status, payload.invoice_id))
        conn.commit()
    return {"paymentId": str(payment_id), "status": new_status, "collected": new_collected, "outstanding": receivable-new_collected}
