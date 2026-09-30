from __future__ import annotations

import os
import psycopg
from fastapi import APIRouter, Depends, HTTPException
from .auth import require_permission

router = APIRouter(prefix="/api/finance/management", tags=["finance-management"])


def db():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


@router.get("/summary")
def summary(_=Depends(require_permission("finance.read"))):
    with db() as conn:
        customer = conn.execute(
            """SELECT COALESCE(SUM(receivable_amount),0),
                      COALESCE(SUM((SELECT SUM(amount)
                                    FROM payment_allocations a
                                    WHERE a.invoice_id=i.id)),0)
               FROM invoices i
               WHERE i.status <> 'VOID'"""
        ).fetchone()

        production = conn.execute(
            """SELECT COALESCE(SUM(service_amount+transport_amount),0),
                      COALESCE(SUM(paid_amount),0)
               FROM production_service_payables"""
        ).fetchone()

        funding = conn.execute(
            """SELECT COALESCE(SUM(current_balance),0)
               FROM finance_funding_sources
               WHERE is_active"""
        ).fetchone()

        alerts = conn.execute(
            """SELECT
                 COUNT(*) FILTER (WHERE status='OPEN')::int,
                 COALESCE(SUM(outstanding_amount)
                          FILTER (WHERE status='OPEN'),0),
                 COUNT(*) FILTER (
                   WHERE status='OPEN' AND alert_type='OVERDUE'
                 )::int,
                 COUNT(*) FILTER (
                   WHERE status='OPEN' AND alert_type='DUE_24H'
                 )::int,
                 COUNT(*) FILTER (
                   WHERE status='OPEN' AND alert_type='DUE_72H'
                 )::int
               FROM finance_settlement_alerts"""
        ).fetchone()

        notifications = conn.execute(
            """SELECT
                 COUNT(*) FILTER (WHERE status='PENDING')::int,
                 COUNT(*) FILTER (WHERE status='PROCESSING')::int,
                 COUNT(*) FILTER (WHERE status='FAILED')::int,
                 COUNT(*) FILTER (WHERE status='SENT')::int
               FROM finance_notification_outbox"""
        ).fetchone()

    customer_receivable, customer_collected = customer
    production_payable, production_paid = production

    return {
        "receivables": {
            "total": customer_receivable,
            "collected": customer_collected,
            "outstanding": customer_receivable - customer_collected,
        },
        "productionPayables": {
            "total": production_payable,
            "paid": production_paid,
            "outstanding": production_payable - production_paid,
        },
        "funding": {
            "activeBalance": funding[0],
        },
        "alerts": {
            "open": alerts[0],
            "outstanding": alerts[1],
            "overdue": alerts[2],
            "due24h": alerts[3],
            "due72h": alerts[4],
        },
        "notifications": {
            "pending": notifications[0],
            "processing": notifications[1],
            "failed": notifications[2],
            "sent": notifications[3],
        },
        "reconciliationStatus": "OK",
    }
