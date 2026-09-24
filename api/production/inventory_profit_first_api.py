"""Inventory capital and Profit First operational control APIs.

This layer consumes finalized month-end inventory snapshots and the existing
Profit First order-control view. Inventory and Profit First remain separate
sources of truth; this module only creates the management-control bridge.
"""
from datetime import date
from decimal import Decimal

import os
import psycopg
from fastapi import APIRouter, Depends, HTTPException

from .auth import require_permission

router = APIRouter(
    prefix="/api/v1/inventory-profit-first",
    tags=["Inventory Profit First"],
)


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


@router.post("/snapshot")
def create_capital_snapshot(
    snapshotDate: date,
    principal: dict = Depends(require_permission("inventory.adjust")),
):
    """Create/update the Profit First management snapshot for a finalized inventory month-end."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*),
                BOOL_AND(status = 'CLOSED'),
                COALESCE(SUM(inventory_value), 0),
                COALESCE(SUM(sellable_qty * unit_cost), 0),
                COALESCE(SUM(reserved_qty * unit_cost), 0),
                COALESCE(SUM(qc_hold_qty * unit_cost), 0)
            FROM inventory_month_end_snapshots
            WHERE snapshot_date = %s
            """,
            (snapshotDate,),
        )
        row = cur.fetchone()
        row_count, all_closed, inv, sellable, reserved, qc_hold = row
        snapshot_status = 'CLOSED' if all_closed else 'NOT_CLOSED'

        if not row_count:
            raise HTTPException(
                404,
                "Finalized inventory month-end snapshot not found",
            )
        if not all_closed:
            raise HTTPException(
                409,
                "Inventory month-end snapshot must be CLOSED before Profit First linkage",
            )

        cur.execute(
            """
            SELECT COALESCE(SUM(variance_value), 0)
            FROM inventory_stock_counts c
            JOIN inventory_month_end_snapshots s ON s.id = c.snapshot_id
            WHERE s.snapshot_date = %s
              AND c.status = 'APPROVED'
            """,
            (snapshotDate,),
        )
        variance = cur.fetchone()[0] or 0

        cur.execute(
            """
            SELECT snapshot_date, inventory_value
            FROM inventory_capital_snapshots
            WHERE snapshot_date < %s
            ORDER BY snapshot_date DESC
            LIMIT 1
            """,
            (snapshotDate,),
        )
        prior = cur.fetchone()
        prior_date = prior[0] if prior else None
        prior_value = Decimal(prior[1]) if prior else Decimal(0)

        inv = Decimal(inv or 0)
        sellable = Decimal(sellable or 0)
        reserved = Decimal(reserved or 0)
        qc_hold = Decimal(qc_hold or 0)
        variance = Decimal(variance or 0)

        change = inv - prior_value if prior else Decimal(0)
        pct = (change / prior_value * 100) if prior_value else Decimal(0)

        period_start = snapshotDate.replace(day=1)
        period_days = (snapshotDate - period_start).days + 1

        cur.execute(
            """
            INSERT INTO inventory_capital_snapshots
                (
                    snapshot_date,
                    inventory_value,
                    sellable_value,
                    reserved_value,
                    qc_hold_value,
                    approved_variance_value,
                    days_since_prior_snapshot,
                    inventory_value_change,
                    capital_change_pct,
                    inventory_snapshot_status,
                    sales_period_start,
                    sales_period_end,
                    sales_period_days,
                    valuation_method
                )
            VALUES
                (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
            ON CONFLICT (snapshot_date) DO UPDATE SET
                inventory_value = EXCLUDED.inventory_value,
                sellable_value = EXCLUDED.sellable_value,
                reserved_value = EXCLUDED.reserved_value,
                qc_hold_value = EXCLUDED.qc_hold_value,
                approved_variance_value = EXCLUDED.approved_variance_value,
                days_since_prior_snapshot = EXCLUDED.days_since_prior_snapshot,
                inventory_value_change = EXCLUDED.inventory_value_change,
                capital_change_pct = EXCLUDED.capital_change_pct,
                inventory_snapshot_status = EXCLUDED.inventory_snapshot_status,
                sales_period_start = EXCLUDED.sales_period_start,
                sales_period_end = EXCLUDED.sales_period_end,
                sales_period_days = EXCLUDED.sales_period_days,
                valuation_method = EXCLUDED.valuation_method
            """,
            (
                snapshotDate,
                inv,
                sellable,
                reserved,
                qc_hold,
                variance,
                (snapshotDate - prior_date).days if prior_date else None,
                change,
                pct,
                snapshot_status,
                period_start,
                snapshotDate,
                period_days,
                "MOVING_AVERAGE",
            ),
        )

    return {
        "snapshotDate": snapshotDate.isoformat(),
        "inventoryValue": inv,
        "inventoryValueChange": change,
        "capitalChangePct": pct,
        "approvedVarianceValue": variance,
        "valuationMethod": "MOVING_AVERAGE",
        "inventorySnapshotStatus": snapshot_status,
        "salesPeriodStart": period_start.isoformat(),
        "salesPeriodEnd": snapshotDate.isoformat(),
    }


@router.get("/summary")
def control_summary(
    snapshotDate: date,
    principal: dict = Depends(require_permission("reporting.read")),
):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM inventory_profit_first_control WHERE snapshot_date = %s",
            (snapshotDate,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                404,
                "Inventory Profit First snapshot not found",
            )
        cols = [d.name for d in cur.description]

    return dict(zip(cols, row))
