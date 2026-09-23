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


@router.get("/operational-summary")
def operational_performance_summary(
    period: Period = Query("month"),
    limit: int | None = Query(None, ge=1, le=120),
    principal: dict = Depends(require_permission("reporting.read")),
):
    """Production execution output attributed to the authenticated performer.

    This endpoint deliberately keeps production quantities separate from
    commercial order counts and from QC finished-goods releases.
    """
    bucket_sql, default_limit = _bucket_sql(period)
    row_limit = limit or default_limit

    # Production operations are the source of operation-level quantities.
    # Duration is derived from the operation timestamps; no manual hours field
    # is introduced here.
    operation_bucket = bucket_sql.replace("order_date", "po.order_date")
    if period == "half_year":
        operation_bucket = (
            "make_date(extract(year from po.order_date)::int, "
            "CASE WHEN extract(month from po.order_date) <= 6 THEN 1 ELSE 7 END, 1)"
        )

    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT
                {operation_bucket} AS bucket,
                COALESCE(po2.performed_by, 'unassigned') AS performed_by,
                po2.operation_code,
                po.product_code,
                COALESCE(SUM(po2.input_qty), 0) AS input_qty,
                COALESCE(SUM(po2.accepted_qty), 0) AS accepted_qty,
                COALESCE(SUM(po2.rejected_qty), 0) AS rejected_qty,
                COALESCE(SUM(po2.waste_qty), 0) AS waste_qty,
                COALESCE(SUM(po2.service_cost + po2.transport_cost), 0) AS operation_cost,
                COALESCE(
                    SUM(EXTRACT(EPOCH FROM (po2.actual_end - po2.actual_start))) / 3600,
                    0
                ) AS actual_hours
            FROM production_operations po2
            JOIN production_orders po
              ON po.id = po2.production_order_id
            WHERE po2.status = 'completed'
            GROUP BY 1,2,3,4
            ORDER BY 1 DESC, 2, 3, 4
            LIMIT %s
            """,
            (row_limit,),
        )
        operations = cur.fetchall()

        # Finished-goods release is the QC gate and is intentionally reported
        # separately from operation accepted_qty to avoid counting the same
        # units twice.
        qc_bucket = (
            "make_date(extract(year from fb.released_at)::int, "
            "CASE WHEN extract(month from fb.released_at) <= 6 THEN 1 ELSE 7 END, 1)"
            if period == "half_year"
            else f"date_trunc('{_PERIODS[period][0]}', fb.released_at)::date"
        )
        cur.execute(
            f"""
            SELECT {qc_bucket} AS bucket,
                   COALESCE(SUM(fb.quantity), 0) AS released_qty
            FROM finished_goods_releases fb
            GROUP BY 1
            ORDER BY 1 DESC
            LIMIT %s
            """,
            (row_limit,),
        )
        qc_rows = cur.fetchall()

    qc_by_bucket = {r[0]: r[1] for r in qc_rows}
    rows = []
    for r in reversed(operations):
        hours = float(r[9] or 0)
        accepted = r[5]
        rows.append({
            "periodStart": r[0],
            "performedBy": r[1],
            "operationCode": r[2],
            "productCode": r[3],
            "inputQty": r[4],
            "acceptedQty": accepted,
            "rejectedQty": r[6],
            "wasteQty": r[7],
            "operationCost": r[8],
            "actualHours": r[9],
            "achievementOutput": accepted,
            "productivityPerHour": float(accepted) / hours if hours > 0 else 0,
            "qualityRatePct": float(accepted) / float(r[4]) * 100 if r[4] else 0,
            "wasteRatePct": float(r[7]) / float(r[4]) * 100 if r[4] else 0,
            "costPerAcceptedUnit": float(r[8]) / float(accepted) if accepted else 0,
            "qcReleasedQtyForPeriod": qc_by_bucket.get(r[0], 0),
        })

    return {
        "period": period,
        "countDefinition": "production_operation_rows",
        "sourceOfTruth": {
            "production": "production_operations",
            "qcFinishedGoods": "finished_goods_releases",
        },
        "rows": rows,
        "qcReleasedByPeriod": [
            {"periodStart": r[0], "releasedQty": r[1]}
            for r in reversed(qc_rows)
        ],
    }
