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


@router.get("/products/by-sku/{sku}")
def product_by_sku(sku: str, _=Depends(require_permission("production.read"))):
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="PostgreSQL adapter is not configured")
    with db.cursor() as cur:
        cur.execute(
            """SELECT id, sku, code128, product_name_fa, product_name_en,
                      product_type, category, brand, unit, status,
                      standard_cost, last_cost, retail_price,
                      distribution_price, wholesale_price
               FROM eyt_product_master WHERE sku = %s""",
            (sku,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product Master SKU not found")
        columns = [d.name for d in cur.description]
    return dict(zip(columns, row))


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

@router.get("/production/{production_order_id}/materials/requirements")
def production_material_requirements(
    production_order_id: int,
    _=Depends(require_permission("production.read")),
):
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="PostgreSQL adapter is not configured")
    with db.cursor() as cur:
        cur.execute(
            """SELECT product_master_id, target_qty
               FROM production_orders WHERE id=%s""",
            (production_order_id,),
        )
        order = cur.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Production order not found")
        product_id, target_qty = order
        if product_id is None:
            raise HTTPException(status_code=409, detail="Production order has no Product Master UUID")
        cur.execute(
            """SELECT b.id, b.bom_code, b.version, b.yield_factor
               FROM eyt_bom b
               WHERE b.product_id=%s AND b.status='ACTIVE'
               ORDER BY b.version DESC LIMIT 1""",
            (product_id,),
        )
        bom = cur.fetchone()
        if not bom:
            raise HTTPException(status_code=404, detail="Active BOM not found")
        bom_id, bom_code, version, yield_factor = bom
        if yield_factor <= 0:
            raise HTTPException(status_code=409, detail="Invalid BOM yield factor")
        cur.execute(
            """SELECT bi.component_product_id, p.sku, p.product_name_fa,
                      bi.quantity_per, bi.scrap_percent, bi.unit,
                      (bi.quantity_per * (1 + bi.scrap_percent / 100.0)
                       * %s / %s) AS required_qty
               FROM eyt_bom_item bi
               JOIN eyt_product_master p ON p.id=bi.component_product_id
               WHERE bi.bom_id=%s
               ORDER BY bi.sequence_no""",
            (target_qty, yield_factor, bom_id),
        )
        rows = cur.fetchall()
        columns = [d.name for d in cur.description]
    return {
        "productionOrderId": production_order_id,
        "productMasterId": str(product_id),
        "targetQty": target_qty,
        "bom": {"id": str(bom_id), "code": bom_code, "version": version, "yieldFactor": yield_factor},
        "materials": [dict(zip(columns, row)) for row in rows],
    }


@router.post("/production/{production_order_id}/actual-cost-snapshot")
def actual_production_cost_snapshot(
    production_order_id: int,
    _=Depends(require_permission("production.write")),
):
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="PostgreSQL adapter is not configured")
    with db.cursor() as cur:
        cur.execute(
            "SELECT eyt_snapshot_actual_production_cost(%s)",
            (production_order_id,),
        )
        snapshot_id = cur.fetchone()[0]
        db.commit()
    return {
        "production_order_id": production_order_id,
        "snapshot_id": str(snapshot_id),
        "cost_basis": "ACTUAL_MATERIAL_CONSUMPTION",
    }


@router.post("/production/{production_order_id}/apply-actual-cost")
def apply_actual_cost_to_order_line(
    production_order_id: int,
    order_no: str,
    order_item_id: int,
    _=Depends(require_permission("finance.write")),
):
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="PostgreSQL adapter is not configured")
    with db.cursor() as cur:
        cur.execute(
            """SELECT eyt_apply_actual_production_cost_to_order_line(%s,%s,%s)""",
            (order_no, order_item_id, production_order_id),
        )
        unit_cost = cur.fetchone()[0]
        db.commit()
    return {
        "production_order_id": production_order_id,
        "order_no": order_no,
        "order_item_id": order_item_id,
        "actual_unit_cost": unit_cost,
        "cost_basis": "ACTUAL_PRODUCTION_COST",
    }


@router.get("/ceo/dashboard")
def ceo_dashboard(_=Depends(require_permission("finance.read"))):
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="PostgreSQL adapter is not configured")
    with db.cursor() as cur:
        cur.execute("""SELECT net_cash_movement, outstanding_receivables,
                              overdue_receivables, high_risk_receivables,
                              net_sales, contribution_profit, contribution_margin,
                              actual_customer_contribution_profit,
                              actual_product_contribution_profit,
                              profitable_product_rows, profitable_customer_rows,
                              generated_at
                       FROM ceo_dashboard""")
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="CEO dashboard data not found")
        columns = [d.name for d in cur.description]
        dashboard = dict(zip(columns, row))

        cur.execute("""SELECT product_id, order_count, units_sold, sales, cogs,
                              contribution_profit, contribution_margin
                       FROM product_profitability_actual
                       ORDER BY contribution_profit DESC
                       LIMIT 10""")
        product_rows = cur.fetchall()
        product_columns = [d.name for d in cur.description]

        cur.execute("""SELECT customer_id, order_count, net_sales,
                              contribution_profit, contribution_margin
                       FROM customer_profitability_actual
                       ORDER BY contribution_profit DESC
                       LIMIT 10""")
        customer_rows = cur.fetchall()
        customer_columns = [d.name for d in cur.description]

    dashboard["top_products"] = [dict(zip(product_columns, r)) for r in product_rows]
    dashboard["top_customers"] = [dict(zip(customer_columns, r)) for r in customer_rows]
    return dashboard
