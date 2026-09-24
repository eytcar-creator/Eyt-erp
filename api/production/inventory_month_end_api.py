"""Month-end inventory control APIs.

The inventory transaction ledger remains the source of truth. These endpoints
create and reconcile a month-end read model; they do not maintain a parallel
live stock balance.
"""
from datetime import date, datetime, time, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import os

from .auth import require_permission

router = APIRouter(prefix="/api/inventory/month-end", tags=["inventory-month-end"])


def _connect():
    import psycopg
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    return psycopg.connect(url)


class StockCountInput(BaseModel):
    snapshot_id: int
    counted_qty: Decimal = Field(ge=0)
    reason_code: str | None = None
    notes: str | None = None


class CountDecisionInput(BaseModel):
    status: str = Field(pattern="^(REVIEW|APPROVED|REJECTED)$")
    notes: str | None = None


@router.post("/snapshot")
def create_snapshot(snapshotDate: date, principal: dict = Depends(require_permission("inventory.adjust"))):
    cutoff = datetime.combine(snapshotDate, time.max, tzinfo=timezone.utc)
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT code FROM warehouses WHERE is_active=TRUE ORDER BY code")
        warehouses = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT product_code FROM products WHERE is_active=TRUE ORDER BY product_code")
        products = [r[0] for r in cur.fetchall()]
        rows = 0
        for warehouse in warehouses:
            for product in products:
                cur.execute("""SELECT COALESCE(SUM(CASE WHEN transaction_type IN ('RECEIPT','TRANSFER_IN','RETURN','PRODUCTION_RECEIPT','ADJUSTMENT') THEN quantity ELSE -quantity END),0), COALESCE(SUM(CASE WHEN transaction_type IN ('RECEIPT','TRANSFER_IN','RETURN','PRODUCTION_RECEIPT','ADJUSTMENT') THEN quantity*unit_cost ELSE 0 END),0), COALESCE(SUM(CASE WHEN transaction_type IN ('RECEIPT','TRANSFER_IN','RETURN','PRODUCTION_RECEIPT','ADJUSTMENT') THEN quantity ELSE 0 END),0) FROM inventory_transactions WHERE warehouse_code=%s AND product_code=%s AND created_at<=%s""",(warehouse,product,cutoff))
                qty, value, receipt_qty = cur.fetchone()
                qty=Decimal(qty or 0); receipt_qty=Decimal(receipt_qty or 0)
                if qty < 0: raise HTTPException(409,f"Negative stock at month-end: {warehouse}/{product}: {qty}")
                unit_cost=Decimal(value or 0)/receipt_qty if receipt_qty else Decimal(0)
                cur.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations WHERE warehouse_code=%s AND product_code=%s AND status='RESERVED' AND created_at<=%s",(warehouse,product,cutoff))
                reserved=Decimal(cur.fetchone()[0] or 0)
                cur.execute("SELECT COALESCE(SUM(quantity),0) FROM finished_goods_releases WHERE warehouse_code=%s AND product_code=%s AND release_status='BLOCKED' AND released_at<=%s",(warehouse,product,cutoff))
                qc_hold=Decimal(cur.fetchone()[0] or 0)
                sellable=max(qty-reserved-qc_hold,Decimal(0))
                cur.execute("""INSERT INTO inventory_month_end_snapshots (snapshot_date,warehouse_code,product_code,physical_qty,reserved_qty,qc_hold_qty,sellable_qty,unit_cost,inventory_value,valuation_method,source_cutoff_at,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'LEDGER_WEIGHTED_AVERAGE',%s,%s) ON CONFLICT (snapshot_date,warehouse_code,product_code) DO UPDATE SET physical_qty=EXCLUDED.physical_qty,reserved_qty=EXCLUDED.reserved_qty,qc_hold_qty=EXCLUDED.qc_hold_qty,sellable_qty=EXCLUDED.sellable_qty,unit_cost=EXCLUDED.unit_cost,inventory_value=EXCLUDED.inventory_value,source_cutoff_at=EXCLUDED.source_cutoff_at WHERE inventory_month_end_snapshots.status<>'CLOSED'""",(snapshotDate,warehouse,product,qty,reserved,qc_hold,sellable,unit_cost,qty*unit_cost,cutoff,principal.get("username","system")))
                rows += 1
    return {"snapshotDate":snapshotDate.isoformat(),"rows":rows,"valuationMethod":"LEDGER_WEIGHTED_AVERAGE","warning":"Operational weighted-average valuation only; accounting-approved cost-layer valuation remains a follow-up."}


@router.get("/summary")
def month_end_summary(snapshot_date: date, principal: dict = Depends(require_permission("reporting.read"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(physical_qty),0),
                   COALESCE(SUM(reserved_qty),0),
                   COALESCE(SUM(qc_hold_qty),0),
                   COALESCE(SUM(sellable_qty),0),
                   COALESCE(SUM(inventory_value),0)
            FROM inventory_month_end_snapshots
            WHERE snapshot_date=%s
            """,
            (snapshot_date,),
        )
        physical, reserved, qc_hold, sellable, value = cur.fetchone()
        cur.execute(
            """
            SELECT COALESCE(SUM(c.variance_qty),0),
                   COALESCE(SUM(c.variance_value),0)
            FROM inventory_stock_counts c
            JOIN inventory_month_end_snapshots s ON s.id=c.snapshot_id
            WHERE s.snapshot_date=%s AND c.status='APPROVED'
            """,
            (snapshot_date,),
        )
        variance_qty, variance_value = cur.fetchone()
    return {
        "snapshotDate": snapshot_date.isoformat(),
        "physicalQty": physical,
        "reservedQty": reserved,
        "qcHoldQty": qc_hold,
        "sellableQty": sellable,
        "inventoryValue": value,
        "approvedVarianceQty": variance_qty,
        "approvedVarianceValue": variance_value,
    }


@router.post("/stock-count")
def record_stock_count(payload: StockCountInput, principal: dict = Depends(require_permission("inventory.adjust"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT physical_qty, unit_cost FROM inventory_month_end_snapshots WHERE id=%s",
            (payload.snapshot_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, "Month-end inventory snapshot not found")
        system_qty, unit_cost = row
        variance = payload.counted_qty - system_qty
        variance_value = variance * unit_cost
        cur.execute(
            """
            INSERT INTO inventory_stock_counts
              (snapshot_id,counted_qty,system_qty,variance_qty,variance_value,
               reason_code,notes,counted_by,counted_at,status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP,'COUNTED')
            RETURNING id
            """,
            (payload.snapshot_id,payload.counted_qty,system_qty,variance,variance_value,
             payload.reason_code,payload.notes,principal.get("username","system")),
        )
        count_id = cur.fetchone()[0]
    return {"id": count_id, "varianceQty": variance, "varianceValue": variance_value}


@router.patch("/stock-count/{count_id}")
def decide_stock_count(count_id: int, payload: CountDecisionInput, principal: dict = Depends(require_permission("inventory.adjust"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE inventory_stock_counts
               SET status=%s, notes=COALESCE(%s,notes),
                   approved_by=%s, approved_at=CASE WHEN %s='APPROVED' THEN CURRENT_TIMESTAMP ELSE approved_at END
             WHERE id=%s
             RETURNING id,status
        """,(payload.status,payload.notes,principal.get("username","system"),payload.status,count_id))
        row=cur.fetchone()
        if row is None:
            raise HTTPException(404,"Stock count not found")
    return {"id":row[0],"status":row[1]}


@router.post("/close")
def close_snapshot(snapshotDate: date, principal: dict = Depends(require_permission("inventory.adjust"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)
            FROM inventory_month_end_snapshots
            WHERE snapshot_date=%s
        """,(snapshotDate,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404,"Month-end snapshot not found")
        cur.execute("""
            SELECT COUNT(*)
            FROM inventory_stock_counts c
            JOIN inventory_month_end_snapshots s ON s.id=c.snapshot_id
            WHERE s.snapshot_date=%s AND c.status IN ('COUNTED','REVIEW')
        """,(snapshotDate,))
        pending=cur.fetchone()[0]
        if pending:
            raise HTTPException(409,f"{pending} stock-count records are not approved/rejected")
        cur.execute("""
            UPDATE inventory_month_end_snapshots
               SET status='CLOSED'
             WHERE snapshot_date=%s AND status<>'CLOSED'
        """,(snapshotDate,))
    return {"snapshotDate":snapshotDate.isoformat(),"status":"CLOSED"}


@router.get("/aging")
def inventory_aging(snapshotDate: date, principal: dict = Depends(require_permission("reporting.read"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT s.product_code,s.warehouse_code,s.physical_qty,s.inventory_value,
                   COALESCE(MAX(t.created_at),s.source_cutoff_at) AS last_movement
            FROM inventory_month_end_snapshots s
            LEFT JOIN inventory_transactions t
              ON t.product_code=s.product_code AND t.warehouse_code=s.warehouse_code
             AND t.created_at<=s.source_cutoff_at
            WHERE s.snapshot_date=%s
            GROUP BY s.id,s.product_code,s.warehouse_code,s.physical_qty,s.inventory_value,s.source_cutoff_at
            ORDER BY last_movement ASC
        """,(snapshotDate,))
        rows=[]
        for product,warehouse,qty,value,last_movement in cur.fetchall():
            days=(snapshotDate-last_movement.date()).days if last_movement else 99999
            bucket="90+" if days>=90 else "60-89" if days>=60 else "30-59" if days>=30 else "0-29"
            rows.append({"productCode":product,"warehouseCode":warehouse,"qty":qty,"value":value,"daysSinceMovement":days,"bucket":bucket})
    return {"snapshotDate":snapshotDate.isoformat(),"rows":rows}
