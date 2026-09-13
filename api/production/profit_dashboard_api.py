from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException, Query

import psycopg

router = APIRouter(prefix="/api/v1/profit-first", tags=["Profit First"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


@router.get("/summary")
def summary(days: int = Query(30, ge=1, le=3650)):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(sales_amount),0), COALESCE(SUM(cogs_amount),0),
                   COALESCE(SUM(gross_profit),0), COALESCE(SUM(collected_cash),0),
                   COALESCE(SUM(outstanding_receivable),0), COALESCE(SUM(invoiced_receivable),0),
                   COALESCE(SUM(operational_cash_contribution),0),
                   CASE WHEN COALESCE(SUM(sales_amount),0)>0
                        THEN ROUND(100*COALESCE(SUM(gross_profit),0)/SUM(sales_amount),2) ELSE 0 END,
                   CASE WHEN COALESCE(SUM(invoiced_receivable),0)>0
                        THEN ROUND(100*COALESCE(SUM(collected_cash),0)/SUM(invoiced_receivable),2) ELSE 0 END
            FROM profit_first_order_control
            WHERE order_date >= CURRENT_DATE - (%s - 1)
        """, (days,))
        row = cur.fetchone()
        cur.execute("""
            SELECT order_date, COALESCE(SUM(sales_amount),0), COALESCE(SUM(collected_cash),0),
                   COALESCE(SUM(gross_profit),0), COALESCE(SUM(operational_cash_contribution),0)
            FROM profit_first_order_control
            WHERE order_date >= CURRENT_DATE - (%s - 1)
            GROUP BY order_date ORDER BY order_date
        """, (days,))
        trend = cur.fetchall()
    return {
        "days": days, "sales": row[0], "cogs": row[1], "grossProfit": row[2],
        "collectedCash": row[3], "outstandingReceivable": row[4], "invoicedReceivable": row[5],
        "operationalCashContribution": row[6], "grossMarginPct": row[7],
        "collectionRealizationPct": row[8],
        "trend": [{"date": r[0], "sales": r[1], "collectedCash": r[2],
                   "grossProfit": r[3], "cashContribution": r[4]} for r in trend],
    }


@router.get("/orders")
def orders(days: int = Query(30, ge=1, le=3650), limit: int = Query(200, ge=1, le=1000)):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT order_no, order_date, customer_id, order_status, sales_amount, cogs_amount,
                   gross_profit, gross_margin_pct, collected_cash, outstanding_receivable,
                   invoiced_receivable, collection_realization_pct, operational_cash_contribution
            FROM profit_first_order_control
            WHERE order_date >= CURRENT_DATE - (%s - 1)
            ORDER BY order_date DESC, order_no DESC LIMIT %s
        """, (days, limit))
        rows = cur.fetchall()
    return [{
        "orderNo": r[0], "orderDate": r[1], "customerId": str(r[2]) if r[2] else None,
        "status": r[3], "sales": r[4], "cogs": r[5], "grossProfit": r[6], "marginPct": r[7],
        "collectedCash": r[8], "outstanding": r[9], "invoicedReceivable": r[10],
        "collectionRealizationPct": r[11], "cashContribution": r[12]
    } for r in rows]
