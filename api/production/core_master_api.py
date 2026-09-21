"""EYT Core Master runtime router.

Provides deterministic read/preview endpoints over the canonical PostgreSQL
views. Database execution is isolated behind a small adapter so the router
does not duplicate business rules.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

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
    order_item_id: UUID,
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
def ceo_dashboard(days: int = 30, _=Depends(require_permission("finance.read"))):
    if days < 1 or days > 3650:
        raise HTTPException(status_code=400, detail="days must be between 1 and 3650")
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="PostgreSQL adapter is not configured")
    with db.cursor() as cur:
        cur.execute("""
            SELECT
              COALESCE(SUM(CASE WHEN type='INFLOW' THEN amount ELSE -amount END),0) AS net_cash_movement,
              (SELECT outstanding_receivables FROM ceo_receivables) AS outstanding_receivables,
              (SELECT overdue_receivables FROM ceo_receivables) AS overdue_receivables,
              (SELECT high_risk_receivables FROM ceo_receivables) AS high_risk_receivables,
              COALESCE((SELECT SUM(i.quantity*i.unit_price) FROM sales_order_items i JOIN sales_orders o ON o.id=i.sales_order_id WHERE o.order_date >= CURRENT_DATE - (%s - 1) AND o.status NOT IN ('DRAFT','PENDING_CONFIRMATION','CANCELLED','RETURNED')),0) AS net_sales,
              COALESCE((SELECT SUM(i.quantity*(i.unit_price-COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0))) FROM sales_order_items i JOIN sales_orders o ON o.id=i.sales_order_id WHERE o.order_date >= CURRENT_DATE - (%s - 1) AND o.status NOT IN ('DRAFT','PENDING_CONFIRMATION','CANCELLED','RETURNED')),0) AS contribution_profit,
              COALESCE((SELECT SUM(i.quantity*(i.unit_price-COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0))) / NULLIF(SUM(i.quantity*i.unit_price),0) FROM sales_order_items i JOIN sales_orders o ON o.id=i.sales_order_id WHERE o.order_date >= CURRENT_DATE - (%s - 1) AND o.status NOT IN ('DRAFT','PENDING_CONFIRMATION','CANCELLED','RETURNED')),0) AS contribution_margin,
              NOW() AS generated_at
            FROM cash_transactions
            WHERE transaction_date >= CURRENT_DATE - (%s - 1)
        """, (days, days, days, days))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="CEO dashboard data not found")
        cols = [d.name for d in cur.description]
        finance = dict(zip(cols, row))

        cur.execute("""
            SELECT COUNT(*) AS orders,
                   COUNT(*) FILTER (WHERE status='CONFIRMED') AS confirmed,
                   COUNT(*) FILTER (WHERE status='FULFILLED') AS fulfilled,
                   COUNT(*) FILTER (WHERE status='CANCELLED') AS cancelled,
                   COALESCE(SUM(subtotal),0) AS sales,
                   COALESCE(SUM(prepayment_amount),0) AS prepayments
            FROM sales_orders
            WHERE order_date >= CURRENT_DATE - (%s - 1)
        """, (days,))
        sales_cols=[d.name for d in cur.description]; sales=dict(zip(sales_cols,cur.fetchone()))

        cur.execute("""
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status NOT IN ('completed','closed','done')) AS open,
                   COUNT(*) FILTER (WHERE planned_end < CURRENT_DATE AND status NOT IN ('completed','closed','done')) AS overdue,
                   COALESCE(SUM(target_qty),0) AS target_qty,
                   COALESCE(SUM(CASE WHEN actual_end IS NOT NULL THEN target_qty ELSE 0 END),0) AS completed_qty
            FROM production_orders
            WHERE order_date >= CURRENT_DATE - (%s - 1)
        """, (days,))
        prod_cols=[d.name for d in cur.description]; production=dict(zip(prod_cols,cur.fetchone()))

        cur.execute("""
            SELECT COALESCE(SUM(quantity * CASE WHEN transaction_type IN ('RECEIPT','TRANSFER_IN','PRODUCTION_RECEIPT','RETURN') THEN 1 ELSE -1 END),0) AS units,
                   COALESCE(SUM(quantity * unit_cost * CASE WHEN transaction_type IN ('RECEIPT','TRANSFER_IN','PRODUCTION_RECEIPT','RETURN') THEN 1 ELSE -1 END),0) AS value
            FROM inventory_transactions
        """)
        inv_cols=[d.name for d in cur.description]; inventory=dict(zip(inv_cols,cur.fetchone()))

        cur.execute("""
            SELECT COUNT(*) AS inspections,
                   COALESCE(SUM(inspected_qty),0) AS inspected_qty,
                   COALESCE(SUM(accepted_qty),0) AS accepted_qty,
                   COALESCE(SUM(rejected_qty),0) AS rejected_qty
            FROM quality_inspections
            WHERE inspection_date >= CURRENT_DATE - (%s - 1)
        """, (days,))
        qc_cols=[d.name for d in cur.description]; qc=dict(zip(qc_cols,cur.fetchone()))

        cur.execute("""
            SELECT COUNT(*) AS open_alerts,
                   COUNT(*) FILTER (WHERE severity='high') AS high_alerts
            FROM production_alerts WHERE status='open'
        """)
        alert_cols=[d.name for d in cur.description]; alerts=dict(zip(alert_cols,cur.fetchone()))

        cur.execute("""
            SELECT i.product_id, COUNT(DISTINCT i.sales_order_id) AS order_count,
                   COALESCE(SUM(i.quantity),0) AS units_sold,
                   COALESCE(SUM(i.quantity*i.unit_price),0) AS sales,
                   COALESCE(SUM(i.quantity*COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0)),0) AS cogs,
                   COALESCE(SUM(i.quantity*(i.unit_price-COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0))),0) AS contribution_profit,
                   CASE WHEN COALESCE(SUM(i.quantity*i.unit_price),0)>0 THEN SUM(i.quantity*(i.unit_price-COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0))) / SUM(i.quantity*i.unit_price) ELSE 0 END AS contribution_margin
            FROM sales_order_items i JOIN sales_orders o ON o.id=i.sales_order_id
            WHERE o.order_date >= CURRENT_DATE - (%s - 1)
              AND o.status NOT IN ('DRAFT','PENDING_CONFIRMATION','CANCELLED','RETURNED')
            GROUP BY i.product_id
            ORDER BY contribution_profit DESC LIMIT 10
        """, (days,))
        pcols=[d.name for d in cur.description]; top_products=[dict(zip(pcols,x)) for x in cur.fetchall()]

        cur.execute("""
            SELECT o.customer_id, COUNT(*) AS order_count,
                   COALESCE(SUM(i.quantity*i.unit_price),0) AS net_sales,
                   COALESCE(SUM(i.quantity*(i.unit_price-COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0))),0) AS contribution_profit,
                   CASE WHEN COALESCE(SUM(i.quantity*i.unit_price),0)>0 THEN SUM(i.quantity*(i.unit_price-COALESCE(i.actual_cost_snapshot,i.cost_snapshot,0))) / SUM(i.quantity*i.unit_price) ELSE 0 END AS contribution_margin
            FROM sales_orders o JOIN sales_order_items i ON i.sales_order_id=o.id
            WHERE o.order_date >= CURRENT_DATE - (%s - 1)
              AND o.status NOT IN ('DRAFT','PENDING_CONFIRMATION','CANCELLED','RETURNED')
            GROUP BY o.customer_id
            ORDER BY contribution_profit DESC LIMIT 10
        """, (days,))
        ccols=[d.name for d in cur.description]; top_customers=[dict(zip(ccols,x)) for x in cur.fetchall()]

        cur.execute("""
            SELECT order_date, COALESCE(SUM(subtotal),0) AS sales,
                   COALESCE(SUM(prepayment_amount),0) AS prepayments
            FROM sales_orders
            WHERE order_date >= CURRENT_DATE - (%s - 1)
              AND status <> 'CANCELLED'
            GROUP BY order_date ORDER BY order_date
        """, (days,))
        trend=[{"date":x[0],"sales":x[1],"prepayments":x[2]} for x in cur.fetchall()]

    qc["acceptance_rate"] = (float(qc["accepted_qty"]) / float(qc["inspected_qty"]) * 100) if qc["inspected_qty"] else 0
    production["completion_rate"] = (float(production["completed_qty"]) / float(production["target_qty"]) * 100) if production["target_qty"] else 0
    return {
        "period_days": days,
        "finance": finance,
        "sales": sales,
        "production": production,
        "inventory": inventory,
        "quality": qc,
        "alerts": alerts,
        "top_products": top_products,
        "top_customers": top_customers,
        "sales_trend": trend,
    }
