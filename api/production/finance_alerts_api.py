from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
import psycopg
from fastapi import APIRouter, Depends, Query
from .auth import require_permission

router=APIRouter(prefix="/api/finance/alerts",tags=["finance-alerts"])

def db():
    url=os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(url)

@router.post("/sync")
def sync(_=Depends(require_permission("finance.write"))):
    now=datetime.utcnow()
    horizon24=now+timedelta(hours=24)
    horizon72=now+timedelta(hours=72)
    created=0
    with db() as conn, conn.cursor() as cur:
        rows=cur.execute("""
          SELECT i.id,i.customer_id,i.invoice_no,i.due_at,
                 i.receivable_amount,
                 COALESCE((SELECT SUM(a.amount) FROM payment_allocations a
                           WHERE a.invoice_id=i.id),0) AS collected
          FROM invoices i
          WHERE i.status <> 'VOID' AND i.due_at IS NOT NULL
        """).fetchall()
        for iid,cid,invoice_no,due,total,collected in rows:
            outstanding=total-collected
            if outstanding <= 0:
                cur.execute("""UPDATE finance_settlement_alerts
                    SET status='RESOLVED',resolved_at=CURRENT_TIMESTAMP
                    WHERE entity_type='CUSTOMER_INVOICE' AND entity_id=%s AND status='OPEN'""",(str(iid),))
                continue
            if due <= now:
                kind,severity="OVERDUE","HIGH"
            elif due <= horizon24:
                kind,severity="DUE_24H","HIGH"
            elif due <= horizon72:
                kind,severity="DUE_72H","MEDIUM"
            else:
                continue
            cur.execute("""UPDATE finance_settlement_alerts
                SET status='RESOLVED',resolved_at=CURRENT_TIMESTAMP
                WHERE entity_type='CUSTOMER_INVOICE' AND entity_id=%s
                  AND status='OPEN' AND alert_type<>%s""",(str(iid),kind))
            exists=cur.execute("""SELECT 1 FROM finance_settlement_alerts
              WHERE alert_type=%s AND entity_type='CUSTOMER_INVOICE'
                AND entity_id=%s AND status='OPEN'""",(kind,str(iid),)).fetchone()
            if not exists:
                message=f"{kind}: invoice {invoice_no}, outstanding {outstanding}"
                cur.execute("""INSERT INTO finance_settlement_alerts
                 (alert_type,entity_type,entity_id,counterparty_name,due_at,
                  outstanding_amount,severity,message)
                 VALUES(%s,'CUSTOMER_INVOICE',%s,%s,%s,%s,%s,%s)
                 RETURNING id""",
                 (kind,str(iid),str(cid),due,outstanding,severity,message))
                alert_id=cur.fetchone()[0]
                payload={"alertId":str(alert_id),"type":kind,"entityType":"CUSTOMER_INVOICE",
                         "entityId":str(iid),"invoiceNo":invoice_no,"customerId":str(cid),
                         "dueAt":due.isoformat() if due else None,"outstanding":str(outstanding),
                         "severity":severity,"message":message}
                cur.execute("""INSERT INTO finance_notification_outbox
                  (event_type,entity_type,entity_id,payload)
                  VALUES(%s,%s,%s,%s::jsonb)""",
                  ("FINANCE_SETTLEMENT_ALERT", "CUSTOMER_INVOICE", str(iid), json.dumps(payload)))
                created+=1
        conn.commit()
    return {"created":created,"syncedAt":now}

@router.get("")
def alerts(status:str=Query("OPEN"),_ = Depends(require_permission("finance.read"))):
    with db() as conn:
        rows=conn.execute("""SELECT id,alert_type,entity_type,entity_id,counterparty_name,
          due_at,outstanding_amount,severity,status,message
          FROM finance_settlement_alerts WHERE status=%s
          ORDER BY due_at NULLS LAST,created_at DESC""",(status,)).fetchall()
    return [{"id":r[0],"type":r[1],"entityType":r[2],"entityId":r[3],
      "counterparty":r[4],"dueAt":r[5],"outstanding":r[6],"severity":r[7],
      "status":r[8],"message":r[9]} for r in rows]

@router.get("/summary")
def summary(_=Depends(require_permission("finance.read"))):
    with db() as conn:
        rows=conn.execute("""
          SELECT alert_type, COUNT(*)::int AS alert_count,
                 COALESCE(SUM(outstanding_amount),0) AS outstanding
          FROM finance_settlement_alerts
          WHERE status='OPEN'
          GROUP BY alert_type
        """).fetchall()
        pending=conn.execute("""
          SELECT COUNT(*)::int
          FROM finance_notification_outbox
          WHERE status='PENDING' AND available_at<=CURRENT_TIMESTAMP
        """).fetchone()[0]
    by_type={
        "DUE_72H":{"count":0,"outstanding":0},
        "DUE_24H":{"count":0,"outstanding":0},
        "OVERDUE":{"count":0,"outstanding":0},
    }
    for kind,count,outstanding in rows:
        by_type.setdefault(kind,{"count":0,"outstanding":0})
        by_type[kind]={"count":count,"outstanding":outstanding}
    total=sum(v["outstanding"] for v in by_type.values())
    return {
        "openAlerts":sum(v["count"] for v in by_type.values()),
        "totalOutstandingInAlerts":total,
        "byType":by_type,
        "pendingNotifications":pending,
    }

@router.get("/outbox")
def outbox(limit:int=Query(100,ge=1,le=500),_=Depends(require_permission("finance.read"))):
    with db() as conn:
        rows=conn.execute("""SELECT id,event_type,entity_type,entity_id,payload,
          status,attempts,available_at,created_at
          FROM finance_notification_outbox
          WHERE status='PENDING' AND available_at<=CURRENT_TIMESTAMP
          ORDER BY id LIMIT %s""",(limit,)).fetchall()
    return [{"id":r[0],"eventType":r[1],"entityType":r[2],"entityId":r[3],
      "payload":r[4],"status":r[5],"attempts":r[6],"availableAt":r[7],
      "createdAt":r[8]} for r in rows]
