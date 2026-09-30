from __future__ import annotations
import os
from datetime import datetime, timedelta
import psycopg
from fastapi import APIRouter, Depends, Query
from .auth import require_permission

router=APIRouter(prefix="/api/finance/alerts",tags=["finance-alerts"])

def db():
    url=os.getenv("DATABASE_URL")
    if not url: raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(url)

@router.post("/sync")
def sync(_=Depends(require_permission("finance.write"))):
    now=datetime.utcnow()
    created=0
    with db() as conn, conn.cursor() as cur:
        rows=cur.execute("""SELECT i.id,i.customer_id,i.receivable_amount,
          COALESCE((SELECT SUM(a.amount) FROM payment_allocations a WHERE a.invoice_id=i.id),0)
          FROM invoices i WHERE i.status <> 'VOID'""").fetchall()
        for iid,cid,total,collected in rows:
            outstanding=total-collected
            if outstanding<=0: continue
            due=cur.execute("SELECT invoice_date FROM invoices WHERE id=%s",(iid,)).fetchone()[0]
            age=now-due
            kind="OVERDUE" if age>timedelta(days=0) else "DUE_24H" if age>=timedelta(days=-1) else "DUE_72H"
            exists=cur.execute("""SELECT 1 FROM finance_settlement_alerts
              WHERE alert_type=%s AND entity_type='CUSTOMER_INVOICE' AND entity_id=%s AND status='OPEN'""",(kind,str(iid))).fetchone()
            if not exists:
                cur.execute("""INSERT INTO finance_settlement_alerts
                 (alert_type,entity_type,entity_id,counterparty_name,due_at,outstanding_amount,severity,message)
                 VALUES(%s,'CUSTOMER_INVOICE',%s,%s,%s,%s,%s,%s)""",
                 (kind,str(iid),str(cid),due,outstanding,"HIGH" if kind=="OVERDUE" else "MEDIUM",
                  f"{kind}: customer invoice {iid}, outstanding {outstanding}"))
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
    return [{"id":r[0],"type":r[1],"entityType":r[2],"entityId":r[3],"counterparty":r[4],
      "dueAt":r[5],"outstanding":r[6],"severity":r[7],"status":r[8],"message":r[9]} for r in rows]
