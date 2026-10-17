"""Read-only E.Y.T AI Finance daily briefing API.

This endpoint composes existing canonical finance views. It deliberately does
not post transactions, alter balances, create forecasts, or mutate ERP data.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import require_permission

router = APIRouter(prefix="/api/v1/ai-finance", tags=["AI Finance"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    return psycopg.connect(url)


def _number(value: Any) -> float:
    return float(value or 0)


@router.get("/daily-brief")
def daily_brief(
    as_of: date = Query(default_factory=date.today),
    window_days: int = Query(30, ge=1, le=3650),
    _=Depends(require_permission("finance.read")),
) -> dict[str, Any]:
    """Return a reproducible, read-only financial snapshot for the requested period."""
    start_date = date.fromordinal(as_of.toordinal() - window_days + 1)
    warnings: list[dict[str, str]] = []
    actions: list[dict[str, Any]] = []

    try:
        with _connect() as conn, conn.cursor() as cur:
            # This ledger contains recorded cash movements, not a reconciled bank balance.
            cur.execute(
                """
                SELECT COUNT(*),
                       COALESCE(SUM(CASE WHEN type='INFLOW' THEN amount ELSE 0 END),0),
                       COALESCE(SUM(CASE WHEN type='OUTFLOW' THEN amount ELSE 0 END),0),
                       MAX(created_at)
                FROM cash_transactions
                WHERE transaction_date >= %s AND transaction_date <= %s
                """,
                (start_date, as_of),
            )
            cash = cur.fetchone()

            cur.execute(
                """
                SELECT COUNT(*),
                       COALESCE(SUM(outstanding),0),
                       COALESCE(SUM(CASE WHEN due_date < %s THEN outstanding ELSE 0 END),0),
                       COALESCE(SUM(CASE WHEN %s - due_date >= 1 AND %s - due_date <= 30
                                         THEN outstanding ELSE 0 END),0),
                       COALESCE(SUM(CASE WHEN %s - due_date BETWEEN 31 AND 60
                                         THEN outstanding ELSE 0 END),0),
                       COALESCE(SUM(CASE WHEN %s - due_date > 60
                                         THEN outstanding ELSE 0 END),0),
                       COUNT(DISTINCT customer_id),
                       MAX(invoice_date)
                FROM receivables
                WHERE invoice_date <= %s AND outstanding > 0
                """,
                (as_of, as_of, as_of, as_of, as_of, as_of),
            )
            receivables = cur.fetchone()

            cur.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(sales),0),
                       COALESCE(SUM(actual_cogs),0),
                       COALESCE(SUM(contribution_profit),0),
                       CASE WHEN COALESCE(SUM(sales),0) > 0
                            THEN ROUND(100 * SUM(contribution_profit) / SUM(sales), 2)
                            ELSE 0 END,
                       MAX(created_at)
                FROM eyt_order_actual_profitability
                WHERE created_at::date >= %s AND created_at::date <= %s
                """,
                (start_date, as_of),
            )
            contribution = cur.fetchone()

            cur.execute(
                """
                SELECT COUNT(*)
                FROM sales_order_items soi
                JOIN sales_orders so ON so.id = soi.sales_order_id
                WHERE so.created_at::date >= %s AND so.created_at::date <= %s
                  AND so.status IN ('CONFIRMED','FULFILLED')
                  AND COALESCE(NULLIF(soi.actual_cost_snapshot,0),
                               NULLIF(soi.cost_snapshot,0)) IS NULL
                """,
                (start_date, as_of),
            )
            missing_cost_rows = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(outstanding_amount),0), MAX(created_at)
                FROM finance_settlement_alerts
                WHERE status='OPEN' AND created_at::date <= %s
                  AND (due_at IS NULL OR due_at::date <= %s)
                """,
                (as_of, as_of),
            )
            payable_alerts = cur.fetchone()
    except HTTPException:
        raise
    except psycopg.Error as exc:
        # A missing or incompatible canonical source must not be replaced with guesses.
        raise HTTPException(
            status_code=503,
            detail="AI Finance source data is unavailable or incompatible; no estimate was generated",
        ) from exc

    cash_count, cash_in, cash_out, cash_updated = cash
    recv_count, recv_total, recv_overdue, age_1_30, age_31_60, age_60_plus, customer_count, recv_updated = receivables
    order_count, sales, cogs, contribution_profit, contribution_margin, contribution_updated = contribution
    alert_count, payable_alert_total, payable_updated = payable_alerts

    if cash_count == 0:
        warnings.append({"code": "NO_CASH_MOVEMENTS", "severity": "HIGH", "message": "در بازه انتخابی گردش نقد ثبت‌شده‌ای وجود ندارد؛ این به معنی صفر بودن موجودی نقد نیست."})
    warnings.append({"code": "CASH_NOT_RECONCILED", "severity": "HIGH", "message": "گردش نقد این گزارش از cash_transactions است و موجودی قابل‌استفاده یا مانده تطبیق‌شده بانکی محسوب نمی‌شود."})
    warnings.append({"code": "CURRENCY_NOT_EXPLICIT", "severity": "MEDIUM", "message": "منبع‌های ترکیب‌شده در این خروجی واحد پول مشترک را به‌صورت صریح ارائه نمی‌کنند؛ جمع‌ها را تا تأیید واحد پول، قطعی تلقی نکنید."})
    warnings.append({"code": "PAYABLES_PARTIAL", "severity": "MEDIUM", "message": "بخش پرداختنی‌ها فقط هشدارهای تسویه باز را نشان می‌دهد و فهرست کامل بدهی‌ها یا تعهدات آتی نیست."})
    warnings.append({"code": "CONTRIBUTION_IS_ORDER_LEVEL", "severity": "MEDIUM", "message": "سود مشارکت این نسخه در سطح سفارش تجمیع شده است، نه SKU/محصول؛ برای تصمیم‌گیری درباره سود هر قطعه، گزارش سودآوری محصول باید جداگانه اعتبارسنجی شود."})
    if missing_cost_rows:
        warnings.append({"code": "MISSING_COSTS", "severity": "HIGH", "message": f"{missing_cost_rows} ردیف فروش در بازه انتخابی فاقد بهای تمام‌شده ثبت‌شده معتبر است؛ سود مشارکت سفارش‌ها ممکن است ناقص باشد."})
        actions.append({
            "action_type": "COMPLETE_COST_RECORDS",
            "summary": "تکمیل بهای تمام‌شده ردیف‌های فروش فاقد هزینه معتبر",
            "estimated_cash_impact": None,
            "urgency": "HIGH",
            "confidence": "HIGH",
            "evidence_refs": ["sales_order_items.actual_cost_snapshot", "sales_order_items.cost_snapshot"],
            "required_human_role": "finance",
            "status": "PROPOSED",
        })
    if _number(recv_overdue) > 0:
        actions.append({
            "action_type": "COLLECT_OVERDUE_RECEIVABLES",
            "summary": "پیگیری مطالبات سررسیدگذشته ثبت‌شده",
            "estimated_cash_impact": None,  # currency is not authoritative in the current source schema
            "urgency": "HIGH",
            "confidence": "MEDIUM",
            "evidence_refs": ["receivables.outstanding", "receivables.due_date"],
            "required_human_role": "finance",
            "status": "PROPOSED",
        })
    actions.sort(key=lambda item: (item["urgency"] != "HIGH", item["estimated_cash_impact"] is None))

    return {
        "as_of": as_of.isoformat(),
        "window_days": window_days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_snapshot": {
            "cash_transactions": {"latest_recorded_at": cash_updated.isoformat() if cash_updated else None, "records": cash_count},
            "receivables": {"latest_invoice_date": recv_updated.isoformat() if recv_updated else None, "open_invoices": recv_count},
            "eyt_order_actual_profitability": {"latest_order_created_at": contribution_updated.isoformat() if contribution_updated else None, "orders": order_count},
            "finance_settlement_alerts": {"latest_alert_created_at": payable_updated.isoformat() if payable_updated else None, "due_open_alerts": alert_count},
            "snapshot_mode": "live_read_only_query",
        },
        "cash_actuals": {
            "status": "RECORDED_MOVEMENTS_NOT_RECONCILED_BALANCE",
            "period_inflow": _number(cash_in),
            "period_outflow": _number(cash_out),
            "period_net_movement": _number(cash_in) - _number(cash_out),
            "available_cash_balance": None,
            "currency": None,
            "source": "cash_transactions",
        },
        "cash_forecast": {"status": "INSUFFICIENT_DATA", "amount": None, "currency": None},
        "receivables": {
            "status": "AVAILABLE" if recv_count else "NO_OPEN_RECEIVABLES",
            "outstanding": _number(recv_total),
            "overdue": _number(recv_overdue),
            "aging": {"1_30_days": _number(age_1_30), "31_60_days": _number(age_31_60), "over_60_days": _number(age_60_plus)},
            "customer_count": customer_count,
            "currency": None,
            "source": "receivables",
        },
        "payables": {
            "status": "PARTIAL_OPEN_ALERTS_ONLY" if alert_count else "INSUFFICIENT_DATA",
            "open_settlement_alert_amount": _number(payable_alert_total),
            "open_settlement_alert_count": alert_count,
            "total_payables": None,
            "currency": None,
            "source": "finance_settlement_alerts",
        },
        "order_contribution": {
            "granularity": "ORDER_LEVEL",
            "status": "AVAILABLE_WITH_COST_WARNINGS" if missing_cost_rows else ("AVAILABLE" if order_count else "INSUFFICIENT_DATA"),
            "orders": order_count,
            "recorded_sales": _number(sales),
            "recorded_cogs": _number(cogs),
            "recorded_contribution_profit": _number(contribution_profit),
            "contribution_margin_pct": _number(contribution_margin),
            "rows_missing_cost": missing_cost_rows,
            "currency": None,
            "source": "eyt_order_actual_profitability",
            "note": "Order-level contribution; not SKU-level product profitability.",
        },
        "working_capital": {"status": "INSUFFICIENT_DATA", "inventory_valuation": None, "wip_valuation": None, "currency": None},
        "data_quality": {"status": "WARNINGS" if warnings else "OK", "warnings": warnings},
        "recommended_actions": actions,
        "mutations_performed": False,
    }
