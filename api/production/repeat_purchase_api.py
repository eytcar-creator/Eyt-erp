from __future__ import annotations

import os
from datetime import date
from typing import Optional

import psycopg
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/repeat-purchase", tags=["Repeat Purchase"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


class ReminderAction(BaseModel):
    channel: Optional[str] = None
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
    return {
        "open": r[0], "overdue": r[1], "dueToday": r[2],
        "due30Days": r[3], "customers": r[4]
    }


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


@router.post("/{reminder_id}/complete")
def complete_reminder(reminder_id: str, order_id: Optional[str] = None):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE repeat_purchase_reminders
            SET status='COMPLETED', completed_at=CURRENT_TIMESTAMP,
                next_order_id=%s, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND status IN ('OPEN','CONTACTED')
            RETURNING id
        """, (order_id, reminder_id))
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
