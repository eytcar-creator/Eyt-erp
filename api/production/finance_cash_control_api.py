from __future__ import annotations
import os
from decimal import Decimal
import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .auth import require_permission

router = APIRouter(prefix="/api/finance/cash-control", tags=["finance-cash-control"])

def _db():
    url=os.getenv("DATABASE_URL")
    if not url: raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)

class FundingSourceIn(BaseModel):
    code: str = Field(min_length=1,max_length=50)
    name: str = Field(min_length=1,max_length=255)
    source_type: str = Field(min_length=1,max_length=30)
    account_reference: str|None = None
    opening_balance: Decimal = Decimal("0")
    currency: str = "IRR"

class MovementIn(BaseModel):
    funding_source_id: int
    direction: str = Field(pattern="^(IN|OUT)$")
    amount: Decimal = Field(gt=0)
    reference_type: str|None = None
    reference_id: str|None = None
    counterparty_name: str|None = None
    description: str|None = None
    created_by: str|None = None

@router.get("/sources")
def sources(_=Depends(require_permission("finance.read"))):
    with _db() as conn:
        rows=conn.execute("""SELECT id,code,name,source_type,account_reference,current_balance,currency,is_active
                             FROM finance_funding_sources ORDER BY name""").fetchall()
    return [{"id":r[0],"code":r[1],"name":r[2],"sourceType":r[3],"accountReference":r[4],
             "currentBalance":r[5],"currency":r[6],"isActive":r[7]} for r in rows]

@router.post("/sources",status_code=201)
def create_source(p: FundingSourceIn,_=Depends(require_permission("finance.write"))):
    with _db() as conn:
        try:
            row=conn.execute("""INSERT INTO finance_funding_sources
                (code,name,source_type,account_reference,opening_balance,current_balance,currency)
                VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (p.code,p.name,p.source_type,p.account_reference,p.opening_balance,p.opening_balance,p.currency)).fetchone()
            conn.commit()
        except psycopg.errors.UniqueViolation as e:
            conn.rollback(); raise HTTPException(409,"funding source code already exists") from e
    return {"id":row[0],"code":p.code}

@router.post("/movements",status_code=201)
def movement(p: MovementIn,_=Depends(require_permission("finance.write"))):
    if p.direction not in ("IN","OUT"): raise HTTPException(422,"invalid direction")
    with _db() as conn:
        with conn.cursor() as cur:
            row=cur.execute("SELECT id,current_balance FROM finance_funding_sources WHERE id=%s AND is_active FOR UPDATE",(p.funding_source_id,)).fetchone()
            if not row: raise HTTPException(404,"funding source not found")
            new_balance=row[1] + p.amount if p.direction=="IN" else row[1] - p.amount
            if new_balance < 0: raise HTTPException(409,"insufficient funding-source balance")
            movement_no=f"FM-{int(__import__('time').time()*1000)}"
            cur.execute("""INSERT INTO finance_cash_movements
                (movement_no,funding_source_id,direction,amount,reference_type,reference_id,counterparty_name,description,created_by)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (movement_no,p.funding_source_id,p.direction,p.amount,p.reference_type,p.reference_id,p.counterparty_name,p.description,p.created_by))
            cur.execute("UPDATE finance_funding_sources SET current_balance=%s WHERE id=%s",(new_balance,p.funding_source_id))
            conn.commit()
    return {"id":row[0],"movementNo":movement_no,"newBalance":new_balance}

@router.get("/alerts")
def alerts(_=Depends(require_permission("finance.read"))):
    with _db() as conn:
        rows=conn.execute("""SELECT id,alert_type,severity,entity_type,entity_id,message,due_at,status
                             FROM finance_alerts WHERE status='OPEN' ORDER BY due_at NULLS LAST, created_at DESC""").fetchall()
    return [{"id":r[0],"type":r[1],"severity":r[2],"entityType":r[3],"entityId":r[4],
             "message":r[5],"dueAt":r[6],"status":r[7]} for r in rows]
