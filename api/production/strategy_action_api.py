from __future__ import annotations

import os
from datetime import date

from fastapi import APIRouter, HTTPException, Query
import psycopg

router = APIRouter(prefix="/api/v1/strategy", tags=["Strategy Action Center"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


@router.get("/actions")
def actions(days: int = Query(30, ge=1, le=3650)):
    """Return deterministic management actions from the existing Profit First source of truth.

    This endpoint deliberately does not create a second KPI/master-data system. It converts
    current ERP metrics into prioritized actions. Thresholds are conservative defaults and
    should later be configurable per company/role.
    """
    with _connect() as conn, conn.cursor() as cur:
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
                     THEN ROUND(100*COALESCE(SUM(gross_profit),0)/SUM(sales_amount),2) ELSE 0 END,
                CASE WHEN COALESCE(SUM(invoiced_receivable),0)>0
                     THEN ROUND(100*COALESCE(SUM(collected_cash),0)/SUM(invoiced_receivable),2) ELSE 0 END
            FROM profit_first_order_control
            WHERE order_date >= CURRENT_DATE - (%s - 1)
            """,
            (days,),
        )
        sales, gross_profit, collected, outstanding, invoiced, cash_contribution, margin, collection = cur.fetchone()

        cur.execute(
            """
            SELECT order_no, order_date, order_status, outstanding_receivable,
                   gross_profit, sales_amount
            FROM profit_first_order_control
            WHERE order_date >= CURRENT_DATE - (%s - 1)
              AND COALESCE(outstanding_receivable,0) > 0
            ORDER BY outstanding_receivable DESC, order_date ASC
            LIMIT 20
            """,
            (days,),
        )
        receivable_rows = cur.fetchall()

    result = []

    def add(priority, key, title, reason, action, metric=None, value=None):
        result.append({
            "id": key,
            "priority": priority,
            "title": title,
            "reason": reason,
            "action": action,
            "metric": metric,
            "value": value,
            "generatedOn": date.today().isoformat(),
            "status": "OPEN",
        })

    if outstanding and float(outstanding) > 0 and (not invoiced or float(invoiced) == 0 or float(collected or 0) / float(invoiced) < 0.80):
        add(
            "CRITICAL",
            "cash-collection",
            "اولویت وصول مطالبات",
            "تحقق وصول کمتر از ۸۰٪ یا وجود مانده مطالبات باز است.",
            "فهرست مطالبات را بررسی و برای بزرگ‌ترین مانده‌ها برنامه وصول امروز ثبت کنید.",
            "outstandingReceivable",
            outstanding,
        )

    if sales and float(sales) > 0 and float(margin or 0) < 20:
        add(
            "HIGH",
            "margin-review",
            "بازبینی حاشیه سود",
            "حاشیه سود ناخالص زیر آستانه ۲۰٪ قرار دارد.",
            "اقلام کم‌حاشیه، قیمت فروش و هزینه واقعی را بررسی و اقلام زیان‌ده را متوقف یا اصلاح کنید.",
            "grossMarginPct",
            margin,
        )

    if sales and float(sales) > 0 and float(cash_contribution or 0) <= 0:
        add(
            "CRITICAL",
            "cash-contribution",
            "مشارکت نقدی منفی/صفر",
            "فروش ثبت شده اما مشارکت نقدی عملیاتی مثبت نیست.",
            "قبل از افزایش خرید یا تولید، هزینه و وصول سفارش‌های جاری را کنترل کنید.",
            "operationalCashContribution",
            cash_contribution,
        )

    if receivable_rows:
        for row in receivable_rows[:5]:
            add(
                "HIGH",
                f"receivable-{row[0]}",
                f"پیگیری سفارش {row[0]}",
                f"مانده وصولی این سفارش {row[3]} است.",
                "وضعیت پرداخت مشتری را بررسی و نتیجه پیگیری را در CRM/مالی ثبت کنید.",
                "orderOutstanding",
                row[3],
            )

    if not result:
        add(
            "INFO",
            "healthy",
            "وضعیت مالی در این بازه هشدار بحرانی ندارد",
            "قواعد فعلی Action Center هشدار فوری ایجاد نکرده‌اند.",
            "رشد را فقط در صورت حفظ حاشیه سود و وصول مناسب ادامه دهید.",
            "grossProfit",
            gross_profit,
        )

    rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}
    result.sort(key=lambda x: (rank[x["priority"]], x["id"]))
    return {
        "days": days,
        "generatedAt": date.today().isoformat(),
        "source": "profit_first_order_control",
        "actions": result,
    }
