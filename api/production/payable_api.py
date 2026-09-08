"""Contractor payable and payment ledger API for production outsourcing."""
from decimal import Decimal
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .auth import require_permission

router = APIRouter(prefix="/api/production/payables", tags=["production-payables"])

def _connect():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(database_url, row_factory=dict_row)

class PaymentInput(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_method: str = Field(min_length=1, max_length=40)
    reference_no: str | None = Field(default=None, max_length=100)
    paid_by: str = Field(min_length=1, max_length=100)
    notes: str | None = None

@router.get("")
def list_payables(order_no: str | None = None, contractor: str | None = None,
                  _=Depends(require_permission("production.read"))):
    with _connect() as conn:
        with conn.cursor() as cur:
            sql = """SELECT p.*, po.order_no,
                     (p.service_amount+p.transport_amount-p.paid_amount) AS balance
                     FROM production_service_payables p
                     JOIN production_orders po ON po.id=p.production_order_id
                     WHERE 1=1"""
            params = []
            if order_no:
                sql += " AND po.order_no=%s"; params.append(order_no)
            if contractor:
                sql += " AND p.contractor_name=%s"; params.append(contractor)
            sql += " ORDER BY p.created_at DESC"
            cur.execute(sql, params)
            return {"items": cur.fetchall()}

@router.post("/{payable_id}/payments", status_code=201)
def record_payment(payable_id: int, payload: PaymentInput,
                   _=Depends(require_permission("production.execute"))):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM production_service_payables WHERE id=%s FOR UPDATE", (payable_id,))
            payable = cur.fetchone()
            if not payable:
                raise HTTPException(status_code=404, detail="Payable not found")
            total = payable["service_amount"] + payable["transport_amount"]
            balance = total - payable["paid_amount"]
            if payload.amount > balance:
                raise HTTPException(status_code=422, detail="payment exceeds outstanding balance")
            cur.execute(
                """INSERT INTO production_payments
                   (payable_id, amount, payment_method, reference_no, paid_by, notes)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""",
                (payable_id, payload.amount, payload.payment_method,
                 payload.reference_no, payload.paid_by, payload.notes),
            )
            payment = cur.fetchone()
            new_paid = payable["paid_amount"] + payload.amount
            status = "paid" if new_paid == total else "partial"
            cur.execute(
                """UPDATE production_service_payables
                   SET paid_amount=%s, status=%s,
                       paid_at=CASE WHEN %s='paid' THEN CURRENT_TIMESTAMP ELSE paid_at END
                   WHERE id=%s RETURNING *""",
                (new_paid, status, status, payable_id),
            )
            updated = cur.fetchone()
            conn.commit()
            return {"payment": payment, "payable": updated, "balance": total-new_paid}
