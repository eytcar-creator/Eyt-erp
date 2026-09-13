from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .auth import require_permission

router = APIRouter(prefix="/api/v1/strategy", tags=["Strategy Action Center"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


class ActionUpdate(BaseModel):
    status: Literal["OPEN", "IN_PROGRESS", "DONE", "DISMISSED"] | None = None
    assigned_to: str | None = Field(default=None, max_length=100)
    due_at: datetime | None = None


class ActionComplete(BaseModel):
    result_note: str = Field(min_length=1, max_length=4000)
    financial_impact: Decimal = Decimal("0")
    realized_cash: Decimal = Decimal("0")
    realized_profit: Decimal = Decimal("0")


def _generated_actions(cur, days: int) -> list[dict]:
    cur.execute(
        """
        SELECT
            COALESCE(SUM(sales_amount),0),
            COALESCE(SUM(gross_profit),0),
            COALESCE(SUM(collected_cash),0),
            COALESCE(SUM(outstanding_receivable),0),
            COALESCE(SUM(invoiced_receivable),0),
            COALESCE(SUM(operational_cash_contribution),0),
            CASE WHEN COALESCE(SUM(sales_amount),0)>0
                 THEN ROUND(100*COALESCE(SUM(gross_profit),0)/SUM(sales_amount),2) ELSE 0 END
        FROM profit_first_order_control
        WHERE order_date >= CURRENT_DATE - (%s - 1)
        """,
        (days,),
    )
    sales, gross_profit, collected, outstanding, invoiced, cash_contribution, margin = cur.fetchone()

    cur.execute(
        """
        SELECT order_no, order_date, outstanding_receivable
        FROM profit_first_order_control
        WHERE order_date >= CURRENT_DATE - (%s - 1)
          AND COALESCE(outstanding_receivable,0) > 0
        ORDER BY outstanding_receivable DESC, order_date ASC
        LIMIT 5
        """,
        (days,),
    )
    receivables = cur.fetchall()
    result: list[dict] = []

    def add(priority, key, title, reason, action, metric=None, value=None, source_ref=None):
        result.append({
            "source_key": key,
            "source_type": "STRATEGY_RULE",
            "source_ref": source_ref,
            "priority": priority,
            "title": title,
            "reason": reason,
            "recommended_action": action,
            "metric": metric,
            "metric_value": value,
        })

    if outstanding and float(outstanding) > 0 and (not invoiced or float(invoiced) == 0 or float(collected or 0) / float(invoiced) < 0.80):
        add("CRITICAL", "cash-collection", "اولویت وصول مطالبات",
            "تحقق وصول کمتر از ۸۰٪ یا وجود مانده مطالبات باز است.",
            "فهرست مطالبات را بررسی و برای بزرگ‌ترین مانده‌ها برنامه وصول امروز ثبت کنید.",
            "outstandingReceivable", outstanding)

    if sales and float(sales) > 0 and float(margin or 0) < 20:
        add("HIGH", "margin-review", "بازبینی حاشیه سود",
            "حاشیه سود ناخالص زیر آستانه ۲۰٪ قرار دارد.",
            "اقلام کم‌حاشیه، قیمت فروش و هزینه واقعی را بررسی و اقلام زیان‌ده را متوقف یا اصلاح کنید.",
            "grossMarginPct", margin)

    if sales and float(sales) > 0 and float(cash_contribution or 0) <= 0:
        add("CRITICAL", "cash-contribution", "مشارکت نقدی منفی/صفر",
            "فروش ثبت شده اما مشارکت نقدی عملیاتی مثبت نیست.",
            "قبل از افزایش خرید یا تولید، هزینه و وصول سفارش‌های جاری را کنترل کنید.",
            "operationalCashContribution", cash_contribution)

    for order_no, order_date, outstanding_value in receivables:
        add("HIGH", f"receivable-{order_no}", f"پیگیری سفارش {order_no}",
            f"مانده وصولی این سفارش {outstanding_value} است.",
            "وضعیت پرداخت مشتری را بررسی و نتیجه پیگیری را در CRM/مالی ثبت کنید.",
            "orderOutstanding", outstanding_value, str(order_no))

    if not result:
        add("INFO", "healthy", "وضعیت مالی در این بازه هشدار بحرانی ندارد",
            "قواعد فعلی Action Center هشدار فوری ایجاد نکرده‌اند.",
            "رشد را فقط در صورت حفظ حاشیه سود و وصول مناسب ادامه دهید.",
            "grossProfit", gross_profit)
    return result


def _sync_actions(cur, actions: list[dict]):
    for a in actions:
        cur.execute(
            """
            INSERT INTO strategy_actions
                (source_key, source_type, source_ref, priority, title, reason,
                 recommended_action, metric, metric_value, generated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
            ON CONFLICT (source_key) DO UPDATE SET
                source_type=EXCLUDED.source_type,
                source_ref=EXCLUDED.source_ref,
                priority=EXCLUDED.priority,
                title=EXCLUDED.title,
                reason=EXCLUDED.reason,
                recommended_action=EXCLUDED.recommended_action,
                metric=EXCLUDED.metric,
                metric_value=EXCLUDED.metric_value,
                generated_at=EXCLUDED.generated_at
            WHERE strategy_actions.status IN ('OPEN','IN_PROGRESS')
            """,
            (a["source_key"], a["source_type"], a["source_ref"], a["priority"],
             a["title"], a["reason"], a["recommended_action"], a["metric"], a["metric_value"]),
        )


def _row(row) -> dict:
    return {
        "id": row[0], "sourceKey": row[1], "sourceType": row[2], "sourceRef": row[3],
        "priority": row[4], "title": row[5], "reason": row[6], "action": row[7],
        "metric": row[8], "value": row[9], "generatedAt": row[10].isoformat() if row[10] else None,
        "status": row[11], "assignedTo": str(row[12]) if row[12] else None,
        "dueAt": row[13].isoformat() if row[13] else None,
        "completedAt": row[14].isoformat() if row[14] else None,
        "resultNote": row[15], "financialImpact": row[16], "realizedCash": row[17],
        "realizedProfit": row[18], "updatedAt": row[19].isoformat() if row[19] else None,
    }


_SELECT = """
SELECT id, source_key, source_type, source_ref, priority, title, reason, recommended_action,
       metric, metric_value, generated_at, status, assigned_to, due_at, completed_at,
       result_note, financial_impact, realized_cash, realized_profit, updated_at
FROM strategy_actions
"""


@router.get("/actions")
def actions(
    days: int = Query(30, ge=1, le=3650),
    status: str | None = Query(None),
    principal: dict = Depends(require_permission("reporting.read")),
):
    del principal
    with _connect() as conn, conn.cursor() as cur:
        generated = _generated_actions(cur, days)
        _sync_actions(cur, generated)
        conn.commit()
        keys = [a["source_key"] for a in generated]
        if status and status not in {"OPEN", "IN_PROGRESS", "DONE", "DISMISSED"}:
            raise HTTPException(400, "Invalid status")
        if not keys:
            return {"days": days, "generatedAt": date.today().isoformat(), "source": "profit_first_order_control", "actions": []}
        if status:
            cur.execute(_SELECT + " WHERE source_key = ANY(%s) AND status=%s ORDER BY CASE priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, id", (keys, status))
        else:
            cur.execute(_SELECT + " WHERE source_key = ANY(%s) ORDER BY CASE priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, id", (keys,))
        rows = cur.fetchall()
    return {"days": days, "generatedAt": date.today().isoformat(), "source": "profit_first_order_control", "actions": [_row(r) for r in rows]}


@router.patch("/actions/{action_id}")
def update_action(
    action_id: int,
    payload: ActionUpdate,
    request: Request,
    principal: dict = Depends(require_permission("reporting.read")),
):
    if payload.status is None and payload.assigned_to is None and payload.due_at is None:
        raise HTTPException(400, "No action fields supplied")
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT status FROM strategy_actions WHERE id=%s FOR UPDATE", (action_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Action not found")
        if payload.assigned_to is not None:
            try:
                import uuid
                uuid.UUID(payload.assigned_to)
            except ValueError:
                raise HTTPException(400, "assigned_to must be a valid user UUID")
        cur.execute(
            """UPDATE strategy_actions SET
               status=COALESCE(%s,status), assigned_to=COALESCE(%s::uuid,assigned_to),
               due_at=COALESCE(%s,due_at), updated_by=%s WHERE id=%s RETURNING id""",
            (payload.status, payload.assigned_to, payload.due_at, principal["id"], action_id),
        )
        if payload.status == "DONE":
            cur.execute("UPDATE strategy_actions SET completed_at=COALESCE(completed_at,now()) WHERE id=%s", (action_id,))
        cur.execute("SELECT action_id FROM (SELECT %s::bigint AS action_id) q", (action_id,))
        conn.commit()
        cur.execute(_SELECT + " WHERE id=%s", (action_id,))
        row = cur.fetchone()
    return _row(row)


@router.post("/actions/{action_id}/complete")
def complete_action(
    action_id: int,
    payload: ActionComplete,
    request: Request,
    principal: dict = Depends(require_permission("reporting.read")),
):
    del request
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """UPDATE strategy_actions
               SET status='DONE', completed_at=now(), result_note=%s,
                   financial_impact=%s, realized_cash=%s, realized_profit=%s, updated_by=%s
               WHERE id=%s
               RETURNING id""",
            (payload.result_note, payload.financial_impact, payload.realized_cash, payload.realized_profit, principal["id"], action_id),
        )
        if not cur.fetchone():
            raise HTTPException(404, "Action not found")
        conn.commit()
        cur.execute(_SELECT + " WHERE id=%s", (action_id,))
        row = cur.fetchone()
    return _row(row)
