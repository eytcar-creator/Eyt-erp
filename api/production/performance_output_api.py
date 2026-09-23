from __future__ import annotations

import os
from datetime import date
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import require_permission

router = APIRouter(prefix="/api/v1/performance", tags=["performance-output"])

Period = Literal["day", "week", "month", "quarter", "half_year", "year"]

_PERIODS = {
    "day": ("day", 30),
    "week": ("week", 12),
    "month": ("month", 12),
    "quarter": ("quarter", 8),
    "year": ("year", 5),
}


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


def _bucket_sql(period: Period) -> tuple[str, int]:
    if period == "half_year":
        return (
            "make_date(extract(year from order_date)::int, "
            "CASE WHEN extract(month from order_date) <= 6 THEN 1 ELSE 7 END, 1)",
            6,
        )
    unit, default_limit = _PERIODS[period]
    return f"date_trunc('{unit}', order_date)::date", default_limit


@router.get("/summary")
def performance_summary(
    period: Period = Query("month"),
    limit: int | None = Query(None, ge=1, le=120),
    principal: dict = Depends(require_permission("reporting.read")),
):
    """
    Executive performance output.

    Count is the number of commercial orders represented by
    profit_first_order_control. Unit-level quantities remain a separate
    production KPI and are intentionally not guessed from financial rows.
    """
    bucket_sql, default_limit = _bucket_sql(period)
    row_limit = limit or default_limit

    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT
                {bucket_sql} AS bucket,
                COUNT(*) AS order_count,
                COALESCE(SUM(sales_amount), 0) AS sales,
                COALESCE(SUM(cogs_amount), 0) AS cogs,
                COALESCE(SUM(gross_profit), 0) AS gross_profit,
                COALESCE(SUM(collected_cash), 0) AS collected_cash,
                COALESCE(SUM(outstanding_receivable), 0) AS outstanding,
                CASE
                    WHEN COALESCE(SUM(sales_amount), 0) > 0
                    THEN ROUND(100 * COALESCE(SUM(gross_profit), 0)
                               / SUM(sales_amount), 2)
                    ELSE 0
                END AS margin_pct
            FROM profit_first_order_control
            GROUP BY 1
            ORDER BY 1 DESC
            LIMIT %s
            """,
            (row_limit,),
        )
        rows = cur.fetchall()

    rows.reverse()
    return {
        "period": period,
        "countDefinition": "commercial_orders",
        "rows": [
            {
                "periodStart": r[0],
                "count": r[1],
                "sales": r[2],
                "cogs": r[3],
                "profit": r[4],
                "collectedCash": r[5],
                "outstanding": r[6],
                "marginPct": r[7],
            }
            for r in rows
        ],
        "totals": {
            "count": sum(r[1] for r in rows),
            "sales": sum((r[2] for r in rows), 0),
            "cogs": sum((r[3] for r in rows), 0),
            "profit": sum((r[4] for r in rows), 0),
            "collectedCash": sum((r[5] for r in rows), 0),
            "outstanding": sum((r[6] for r in rows), 0),
        },
    }
