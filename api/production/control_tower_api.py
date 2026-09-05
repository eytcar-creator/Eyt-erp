from decimal import Decimal
import os

from fastapi import APIRouter, Depends, HTTPException

from .auth import require_permission

router = APIRouter(prefix="/api/production/control-tower", tags=["production-control-tower"])


def _connect():
    import psycopg
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    return psycopg.connect(database_url)


@router.get("/live")
def live_control_tower(_=Depends(require_permission("production.read"))):
    """Return the live production board from PostgreSQL without mock data."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    po.order_no,
                    po.product_code,
                    po.product_name,
                    po.target_qty,
                    po.planned_start,
                    po.planned_end,
                    po.actual_start,
                    po.status AS order_status,
                    op.sequence_no,
                    op.operation_code,
                    op.operation_name,
                    op.contractor_name,
                    op.planned_start AS operation_planned_start,
                    op.planned_end AS operation_planned_end,
                    op.actual_start,
                    op.actual_end,
                    op.input_qty,
                    op.accepted_qty,
                    op.rejected_qty,
                    op.waste_qty,
                    op.service_cost,
                    op.transport_cost,
                    op.status AS operation_status
                FROM production_orders po
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM production_operations x
                    WHERE x.production_order_id = po.id
                    ORDER BY
                        CASE WHEN x.status NOT IN ('completed', 'cancelled') THEN 0 ELSE 1 END,
                        x.sequence_no DESC
                    LIMIT 1
                ) op ON TRUE
                WHERE po.status NOT IN ('completed', 'cancelled')
                ORDER BY COALESCE(op.planned_end, po.planned_end, CURRENT_DATE), po.order_no
                """
            )
            rows = cur.fetchall()
            columns = [d.name for d in cur.description]

            orders = []
            for row in rows:
                r = dict(zip(columns, row))
                accepted = Decimal(r["accepted_qty"] or 0)
                rejected = Decimal(r["rejected_qty"] or 0)
                waste = Decimal(r["waste_qty"] or 0)
                input_qty = Decimal(r["input_qty"] or 0)
                remaining = max(input_qty - accepted - rejected - waste, Decimal("0"))
                orders.append({
                    "orderNo": r["order_no"],
                    "productCode": r["product_code"],
                    "productName": r["product_name"],
                    "targetQty": r["target_qty"],
                    "plannedStart": r["planned_start"],
                    "plannedEnd": r["planned_end"],
                    "actualStart": r["actual_start"],
                    "orderStatus": r["order_status"],
                    "currentOperation": {
                        "sequenceNo": r["sequence_no"],
                        "code": r["operation_code"],
                        "name": r["operation_name"],
                        "contractor": r["contractor_name"],
                        "plannedStart": r["operation_planned_start"],
                        "plannedEnd": r["operation_planned_end"],
                        "actualStart": r["actual_start"],
                        "actualEnd": r["actual_end"],
                        "status": r["operation_status"],
                        "inputQty": input_qty,
                        "acceptedQty": accepted,
                        "rejectedQty": rejected,
                        "wasteQty": waste,
                        "remainingQty": remaining,
                        "serviceCost": r["service_cost"] or Decimal("0"),
                        "transportCost": r["transport_cost"] or Decimal("0"),
                    } if r["operation_code"] else None,
                })

            return {
                "generatedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                "source": "postgresql",
                "orders": orders,
                "openOrders": len(orders),
            }
    finally:
        conn.close()
