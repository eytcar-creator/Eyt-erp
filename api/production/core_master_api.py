"""EYT Core Master runtime router.

Provides deterministic read/preview endpoints over the canonical PostgreSQL
views. Database execution is isolated behind a small adapter so the router
does not duplicate business rules.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .auth import require_permission

router = APIRouter(prefix="/api/v1/core", tags=["eyt-core"])


def _db():
    try:
        from .postgres_adapter import get_connection
        return get_connection()
    except (ImportError, AttributeError):
        return None


@router.get("/products/{product_id}/standard-cost")
def product_standard_cost(product_id: str, _=Depends(require_permission("production.read"))):
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="PostgreSQL adapter is not configured")
    with db.cursor() as cur:
        cur.execute(
            """SELECT product_id, sku, product_name_fa, bom_material_cost,
                      routing_operation_cost, calculated_standard_cost, production_days
               FROM eyt_product_standard_cost WHERE product_id = %s""",
            (product_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product cost not found")
    return row


@router.get("/products/{product_id}/bom")
def product_bom(product_id: str, _=Depends(require_permission("production.read"))):
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="PostgreSQL adapter is not configured")
    with db.cursor() as cur:
        cur.execute(
            """SELECT b.id, b.bom_code, b.version, b.status,
                      bi.sequence_no, bi.component_product_id,
                      p.sku, p.product_name_fa, bi.quantity_per,
                      bi.unit, bi.scrap_percent
               FROM eyt_bom b
               JOIN eyt_bom_item bi ON bi.bom_id = b.id
               JOIN eyt_product_master p ON p.id = bi.component_product_id
               WHERE b.product_id = %s
               ORDER BY b.version DESC, bi.sequence_no""",
            (product_id,),
        )
        rows = cur.fetchall()
    return rows


@router.get("/products/{product_id}/routing")
def product_routing(product_id: str, _=Depends(require_permission("production.read"))):
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="PostgreSQL adapter is not configured")
    with db.cursor() as cur:
        cur.execute(
            """SELECT r.id, r.routing_code, r.version, r.status,
                      ro.sequence_no, ro.operation_code, ro.operation_name_fa,
                      ro.make_or_buy, ro.work_center, ro.planned_days,
                      ro.capacity_per_day, ro.unit_cost, ro.transport_cost_per_unit,
                      ro.qc_required
               FROM eyt_routing r
               JOIN eyt_routing_operation ro ON ro.routing_id = r.id
               WHERE r.product_id = %s
               ORDER BY r.version DESC, ro.sequence_no""",
            (product_id,),
        )
        rows = cur.fetchall()
    return rows


@router.post("/production/{production_order_id}/cost-snapshot")
def production_cost_snapshot(production_order_id: int, _=Depends(require_permission("production.write"))):
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="PostgreSQL adapter is not configured")
    with db.cursor() as cur:
        cur.execute("SELECT eyt_snapshot_production_cost(%s)", (production_order_id,))
        snapshot_id = cur.fetchone()[0]
        db.commit()
    return {"production_order_id": production_order_id, "snapshot_id": str(snapshot_id)}
