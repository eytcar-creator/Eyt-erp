from __future__ import annotations
import os
import psycopg
from fastapi import APIRouter, Depends, HTTPException
from .auth import require_permission
from .finance_reconciliation_rules import evaluate_reconciliation

router = APIRouter(prefix="/api/finance/reconciliation", tags=["finance-reconciliation"])

def db():
    url=os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)

@router.get("/summary")
def summary(_=Depends(require_permission("finance.read"))):
    with db() as conn:
        customer=conn.execute("""SELECT COALESCE(SUM(receivable_amount),0),
            COALESCE(SUM((SELECT SUM(amount) FROM payment_allocations a WHERE a.invoice_id=i.id)),0)
            FROM invoices i WHERE i.status <> 'VOID'""").fetchone()
        production=conn.execute("""SELECT COALESCE(SUM(service_amount+transport_amount),0),
            COALESCE(SUM(paid_amount),0) FROM production_service_payables""").fetchone()
        funding=conn.execute("""SELECT COALESCE(SUM(current_balance),0)
            FROM finance_funding_sources WHERE is_active""").fetchone()

    result = evaluate_reconciliation(
        customer[0], customer[1], production[0], production[1], funding[0]
    )
    return {
        "customerReceivable": customer[0],
        "customerCollected": customer[1],
        "customerOutstanding": customer[0]-customer[1],
        "productionPayable": production[0],
        "productionPaid": production[1],
        "productionOutstanding": production[0]-production[1],
        "activeFundingBalance": funding[0],
        "reconciliationStatus": result.status,
        "issues": list(result.issues),
    }
