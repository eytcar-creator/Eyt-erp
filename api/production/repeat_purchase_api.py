from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/repeat-purchase", tags=["Repeat Purchase"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


class ReminderAction(BaseModel):
    channel: Optional[str] = None
    notes: Optional[str] = None


class ReorderIn(BaseModel):
    warehouseCode: str = Field(default="MAIN", max_length=60)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unitPrice: Optional[Decimal] = Field(default=None, ge=0)
    prepaymentAmount: Decimal = Field(default=Decimal("0"), ge=0)
    sourceChannel: str = Field(default="REPEAT_PURCHASE", max_length=50)
    notes: Optional[str] = None


@router.get("/opportunities")
def opportunities(
    status: str = "OPEN",
    overdue_only: bool = False,
    limit: int = Query(200, ge=1, le=1000),
):
    with _connect() as conn, conn.cursor() as cur:
        sql = """
            SELECT id, customer_id, customer_code, customer_name, phone,
                   customer_vehicle_id, product_id, product_code, product_name,
                   due_date, status, days_overdue
            FROM repeat_purchase_opportunities
            WHERE status=%s
        """
        params = [status]
        if overdue_only:
            sql += " AND days_overdue > 0"
        sql += " ORDER BY days_overdue DESC, due_date ASC LIMIT %s"
        params.append(limit)
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [
        {
            "id": str(r[0]), "customerId": str(r[1]), "customerCode": r[2],
            "customerName": r[3], "phone": r[4], "customerVehicleId": str(r[5]) if r[5] else None,
            "productId": str(r[6]), "productCode": r[7], "productName": r[8],
            "dueDate": r[9], "status": r[10], "daysOverdue": r[11]
        }
        for r in rows
    ]


@router.get("/summary")
def summary():
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT
              COUNT(*) FILTER (WHERE status='OPEN') AS open_count,
              COUNT(*) FILTER (WHERE status='OPEN' AND due_date < CURRENT_DATE) AS overdue_count,
              COUNT(*) FILTER (WHERE status='OPEN' AND due_date = CURRENT_DATE) AS due_today,
              COUNT(*) FILTER (WHERE status='OPEN' AND due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 30) AS due_30,
              COUNT(DISTINCT customer_id) FILTER (WHERE status='OPEN') AS customers
            FROM repeat_purchase_reminders
        """)
        r = cur.fetchone()
    return {"open": r[0], "overdue": r[1], "dueToday": r[2], "due30Days": r[3], "customers": r[4]}


@router.post("/{reminder_id}/contact")
def mark_contacted(reminder_id: str, payload: ReminderAction):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE repeat_purchase_reminders
            SET status='CONTACTED', contact_channel=%s, contacted_at=CURRENT_TIMESTAMP,
                notes=COALESCE(%s, notes), updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND status='OPEN'
            RETURNING id
        """, (payload.channel, payload.notes, reminder_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Open reminder not found")
        conn.commit()
    return {"id": str(row[0]), "status": "CONTACTED"}


@router.post("/{reminder_id}/reorder")
def create_reorder(reminder_id: str, payload: ReorderIn):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT r.id,r.customer_id,r.customer_vehicle_id,r.product_id,c.customer_code,
                   p.product_code,p.sale_price,p.purchase_price
            FROM repeat_purchase_reminders r
            JOIN customers c ON c.id=r.customer_id
            JOIN products p ON p.id=r.product_id
            WHERE r.id=%s AND r.status IN ('OPEN','CONTACTED')
            FOR UPDATE OF r
        """, (reminder_id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(404, "Active reminder not found")

        reminder, customer_id, vehicle_id, product_id, customer_code, product_code, sale_price, purchase_price = r
        unit_price = payload.unitPrice if payload.unitPrice is not None else Decimal(str(sale_price or 0))
        subtotal = payload.quantity * unit_price
        if payload.prepaymentAmount > subtotal:
            raise HTTPException(400, "prepaymentAmount cannot exceed subtotal")

        cur.execute("SELECT 1 FROM warehouses WHERE code=%s AND is_active", (payload.warehouseCode,))
        if not cur.fetchone():
            raise HTTPException(400, "Warehouse is not active")

        order_no = f"RP-{date.today().strftime('%Y%m%d')}-{str(reminder)[:8].upper()}"
        cur.execute("""
            INSERT INTO sales_orders(
                order_no,customer_id,warehouse_code,order_date,status,subtotal,prepayment_amount,
                customer_vehicle_id,source_type,source_id,source_channel,channel,notes
            ) VALUES(%s,%s,%s,CURRENT_DATE,'DRAFT',%s,%s,%s,'REPEAT_PURCHASE',%s,%s,'REPEAT_PURCHASE',%s)
            RETURNING id,order_no
        """, (order_no,customer_id,payload.warehouseCode,subtotal,payload.prepaymentAmount,
              vehicle_id,reminder,payload.sourceChannel,payload.notes))
        order_id, order_no = cur.fetchone()

        cur.execute("""
            INSERT INTO sales_order_items(sales_order_id,product_id,quantity,unit_price,unit_cost)
            VALUES(%s,%s,%s,%s,%s)
        """, (order_id,product_id,payload.quantity,unit_price,purchase_price or 0))

        cur.execute("""
            UPDATE repeat_purchase_reminders
            SET status='COMPLETED', completed_at=CURRENT_TIMESTAMP,
                completed_order_id=%s, next_order_id=%s, updated_at=CURRENT_TIMESTAMP,
                notes=COALESCE(%s, notes)
            WHERE id=%s AND status IN ('OPEN','CONTACTED')
        """, (order_id,order_id,payload.notes,reminder))
        conn.commit()

    return {
        "orderId": str(order_id), "orderNo": order_no, "customerCode": customer_code,
        "productCode": product_code, "quantity": payload.quantity,
        "unitPrice": unit_price, "subtotal": subtotal, "status": "DRAFT"
    }


@router.post("/{reminder_id}/complete")
def complete_reminder(reminder_id: str, order_id: Optional[str] = None):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE repeat_purchase_reminders
            SET status='COMPLETED', completed_at=CURRENT_TIMESTAMP,
                next_order_id=%s, completed_order_id=%s, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND status IN ('OPEN','CONTACTED')
            RETURNING id
        """, (order_id, order_id, reminder_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Active reminder not found")
        conn.commit()
    return {"id": str(row[0]), "status": "COMPLETED"}


@router.post("/{reminder_id}/cancel")
def cancel_reminder(reminder_id: str, payload: ReminderAction):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE repeat_purchase_reminders
            SET status='CANCELLED', notes=COALESCE(%s, notes), updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND status IN ('OPEN','CONTACTED')
            RETURNING id
        """, (payload.notes, reminder_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Active reminder not found")
        conn.commit()
    return {"id": str(row[0]), "status": "CANCELLED"}
