from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import psycopg


def db():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(url)


def sync_settlement_alerts() -> dict:
    """Reconcile invoice due dates into settlement alerts and notification outbox.

    This service owns alert projection only. It does not alter the financial
    ledger or payment allocations.
    """
    now = datetime.utcnow()
    horizon24 = now + timedelta(hours=24)
    horizon72 = now + timedelta(hours=72)
    created = 0
    resolved = 0

    with db() as conn, conn.cursor() as cur:
        rows = cur.execute(
            """
            SELECT i.id,i.customer_id,i.invoice_no,i.due_at,
                   i.receivable_amount,
                   COALESCE((
                     SELECT SUM(a.amount)
                     FROM payment_allocations a
                     WHERE a.invoice_id=i.id
                   ),0) AS collected
            FROM invoices i
            WHERE i.status <> 'VOID' AND i.due_at IS NOT NULL
            """
        ).fetchall()

        for iid, cid, invoice_no, due, total, collected in rows:
            outstanding = total - collected

            if outstanding <= 0:
                cur.execute(
                    """
                    UPDATE finance_settlement_alerts
                    SET status='RESOLVED',resolved_at=CURRENT_TIMESTAMP
                    WHERE entity_type='CUSTOMER_INVOICE'
                      AND entity_id=%s AND status='OPEN'
                    """,
                    (str(iid),),
                )
                resolved += cur.rowcount
                continue

            if due <= now:
                kind, severity = "OVERDUE", "HIGH"
            elif due <= horizon24:
                kind, severity = "DUE_24H", "HIGH"
            elif due <= horizon72:
                kind, severity = "DUE_72H", "MEDIUM"
            else:
                continue

            cur.execute(
                """
                UPDATE finance_settlement_alerts
                SET status='RESOLVED',resolved_at=CURRENT_TIMESTAMP
                WHERE entity_type='CUSTOMER_INVOICE' AND entity_id=%s
                  AND status='OPEN' AND alert_type<>%s
                """,
                (str(iid), kind),
            )
            resolved += cur.rowcount

            exists = cur.execute(
                """
                SELECT 1 FROM finance_settlement_alerts
                WHERE alert_type=%s AND entity_type='CUSTOMER_INVOICE'
                  AND entity_id=%s AND status='OPEN'
                """,
                (kind, str(iid)),
            ).fetchone()

            if exists:
                continue

            message = f"{kind}: invoice {invoice_no}, outstanding {outstanding}"
            cur.execute(
                """
                INSERT INTO finance_settlement_alerts
                  (alert_type,entity_type,entity_id,counterparty_name,due_at,
                   outstanding_amount,severity,message)
                VALUES(%s,'CUSTOMER_INVOICE',%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (kind, str(iid), str(cid), due, outstanding, severity, message),
            )
            alert_id = cur.fetchone()[0]

            payload = {
                "alertId": str(alert_id),
                "type": kind,
                "entityType": "CUSTOMER_INVOICE",
                "entityId": str(iid),
                "invoiceNo": invoice_no,
                "customerId": str(cid),
                "dueAt": due.isoformat() if due else None,
                "outstanding": str(outstanding),
                "severity": severity,
                "message": message,
            }
            cur.execute(
                """
                INSERT INTO finance_notification_outbox
                  (event_type,entity_type,entity_id,payload)
                VALUES(%s,%s,%s,%s::jsonb)
                """,
                (
                    "FINANCE_SETTLEMENT_ALERT",
                    "CUSTOMER_INVOICE",
                    str(iid),
                    json.dumps(payload),
                ),
            )
            created += 1

        conn.commit()

    return {
        "created": created,
        "resolved": resolved,
        "syncedAt": now,
    }
