"""Inventory capital and Profit First control APIs."""
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
import os
import psycopg
from .auth import require_permission

router = APIRouter(prefix="/api/v1/inventory-profit-first", tags=["Inventory Profit First"])

def _connect():
    url=os.getenv("DATABASE_URL")
    if not url: raise HTTPException(503,"DATABASE_URL is not configured")
    return psycopg.connect(url)

@router.post("/snapshot")
def create_capital_snapshot(snapshotDate: date, principal: dict = Depends(require_permission("inventory.adjust"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(inventory_value),0),
                   COALESCE(SUM(sellable_qty*unit_cost),0),
                   COALESCE(SUM(reserved_qty*unit_cost),0),
                   COALESCE(SUM(qc_hold_qty*unit_cost),0)
            FROM inventory_month_end_snapshots WHERE snapshot_date=%s
        """,(snapshotDate,))
        inv,sellable,reserved,qc=cur.fetchone()
        cur.execute("""
            SELECT COALESCE(SUM(variance_value),0)
            FROM inventory_stock_counts c
            JOIN inventory_month_end_snapshots s ON s.id=c.snapshot_id
            WHERE s.snapshot_date=%s AND c.status='APPROVED'
        """,(snapshotDate,))
        variance=cur.fetchone()[0] or 0
        cur.execute("""
            SELECT inventory_value FROM inventory_capital_snapshots
            WHERE snapshot_date < %s ORDER BY snapshot_date DESC LIMIT 1
        """,(snapshotDate,))
        prior=cur.fetchone()
        prior_value=Decimal(prior[0]) if prior else Decimal(0)
        inv=Decimal(inv or 0)
        change=inv-prior_value if prior else Decimal(0)
        pct=(change/prior_value*100) if prior_value else Decimal(0)
        cur.execute("""
            INSERT INTO inventory_capital_snapshots
              (snapshot_date,inventory_value,sellable_value,reserved_value,qc_hold_value,
               approved_variance_value,inventory_value_change,capital_change_pct,days_since_prior_snapshot)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,
              (SELECT %s::date - snapshot_date FROM inventory_capital_snapshots
               WHERE snapshot_date < %s ORDER BY snapshot_date DESC LIMIT 1))
            ON CONFLICT(snapshot_date) DO UPDATE SET
              inventory_value=EXCLUDED.inventory_value,sellable_value=EXCLUDED.sellable_value,
              reserved_value=EXCLUDED.reserved_value,qc_hold_value=EXCLUDED.qc_hold_value,
              approved_variance_value=EXCLUDED.approved_variance_value,
              inventory_value_change=EXCLUDED.inventory_value_change,
              capital_change_pct=EXCLUDED.capital_change_pct
        """,(snapshotDate,inv,sellable,reserved,qc,variance,change,pct,snapshotDate,snapshotDate))
    return {"snapshotDate":snapshotDate.isoformat(),"inventoryValue":inv,"inventoryValueChange":change,
            "capitalChangePct":pct,"approvedVarianceValue":variance}

@router.get("/summary")
def control_summary(snapshotDate: date, principal: dict = Depends(require_permission("reporting.read"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM inventory_profit_first_control WHERE snapshot_date=%s",(snapshotDate,))
        row=cur.fetchone()
        if not row: raise HTTPException(404,"Inventory Profit First snapshot not found")
        cols=[d.name for d in cur.description]
    return dict(zip(cols,row))
