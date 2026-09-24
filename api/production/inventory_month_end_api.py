"""Month-end inventory control APIs.

The inventory transaction ledger remains the source of truth. These endpoints
create and reconcile a month-end read model; they do not maintain a parallel
live stock balance.
"""
from datetime import date, datetime, time, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .dependencies import require_permission
from .database import get_db

router = APIRouter(prefix="/api/v1/inventory/month-end", tags=["inventory-month-end"])


class StockCountInput(BaseModel):
    snapshot_id: int
    counted_qty: Decimal = Field(ge=0)
    reason_code: str | None = None
    notes: str | None = None


@router.get("/summary")
def month_end_summary(snapshot_date: date, principal: dict = Depends(require_permission("reporting.read"))):
    with get_db() as conn, conn.cursor() as cur:
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
    with get_db() as conn, conn.cursor() as cur:
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
