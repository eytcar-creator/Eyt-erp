"""Production material issue/return and WIP transfer contracts."""
from decimal import Decimal
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from .auth import require_permission

router = APIRouter(prefix="/api/production", tags=["production-inventory"])

class ProductionMovement(BaseModel):
    documentNo: str = Field(min_length=1, max_length=100)
    orderNo: str = Field(min_length=1, max_length=100)
    sku: str = Field(min_length=1, max_length=100)
    warehouse: str = Field(default="MAIN", min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    unitCost: Decimal = Field(default=Decimal("0"), ge=0)
    operationCode: str | None = None
    notes: str | None = None

class WipTransfer(BaseModel):
    documentNo: str = Field(min_length=1, max_length=100)
    orderNo: str = Field(min_length=1, max_length=100)
    sku: str = Field(min_length=1, max_length=100)
    warehouse: str = Field(default="MAIN", min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    fromOperationCode: str | None = None
    toOperationCode: str | None = None
    notes: str | None = None

def _connect():
    import psycopg
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)

def _order_id(cur, order_no: str):
    cur.execute("SELECT id FROM production_orders WHERE order_no=%s", (order_no,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"Production order not found: {order_no}")
    return row[0]

def _post(cur, p, movement_type):
    cur.execute("""INSERT INTO inventory_transactions
      (document_no,warehouse_code,product_code,quantity,unit,transaction_type,reference_type,reference_id,unit_cost)
      VALUES (%s,%s,%s,%s,'PCS',%s,'PRODUCTION',%s,%s) RETURNING id""",
      (p.documentNo,p.warehouse,p.sku,p.quantity,movement_type,p.orderNo,p.unitCost))
    return cur.fetchone()[0]

@router.post("/orders/{order_no}/materials/issue", status_code=201)
def issue_material(order_no: str, p: ProductionMovement, request: Request,
                   principal: dict = Depends(require_permission("production.execute"))):
    if p.orderNo != order_no:
        raise HTTPException(409, "orderNo does not match URL")
    with _connect() as conn, conn.cursor() as cur:
        order_id = _order_id(cur, order_no)
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"{p.sku}:{p.warehouse}",))
        cur.execute("""SELECT COALESCE(SUM(CASE WHEN transaction_type IN
          ('RECEIPT','TRANSFER_IN','RETURN','PRODUCTION_RECEIPT','ADJUSTMENT') THEN quantity ELSE -quantity END),0)
          FROM inventory_transactions WHERE product_code=%s AND warehouse_code=%s""", (p.sku,p.warehouse))
        on_hand = cur.fetchone()[0]
        if on_hand < p.quantity:
            raise HTTPException(409, f"Insufficient stock for {p.sku}: available={on_hand}, requested={p.quantity}")
        tx = _post(cur,p,"ISSUE")
        cur.execute("""INSERT INTO production_material_movements
          (production_order_id,material_code,warehouse_code,quantity,movement_type,document_no,actor_name,notes)
          VALUES (%s,%s,%s,%s,'ISSUE',%s,%s,%s)""",
          (order_id,p.sku,p.warehouse,p.quantity,p.documentNo,principal["username"],p.notes))
    return {"documentNo":p.documentNo,"orderNo":order_no,"transactionId":tx,"status":"issued"}

@router.post("/orders/{order_no}/materials/return", status_code=201)
def return_material(order_no: str, p: ProductionMovement, request: Request,
                    principal: dict = Depends(require_permission("production.execute"))):
    if p.orderNo != order_no:
        raise HTTPException(409, "orderNo does not match URL")
    with _connect() as conn, conn.cursor() as cur:
        order_id = _order_id(cur, order_no)
        tx = _post(cur,p,"RETURN")
        cur.execute("""INSERT INTO production_material_movements
          (production_order_id,material_code,warehouse_code,quantity,movement_type,document_no,actor_name,notes)
          VALUES (%s,%s,%s,%s,'RETURN',%s,%s,%s)""",
          (order_id,p.sku,p.warehouse,p.quantity,p.documentNo,principal["username"],p.notes))
    return {"documentNo":p.documentNo,"orderNo":order_no,"transactionId":tx,"status":"returned"}

@router.post("/orders/{order_no}/wip/transfer", status_code=201)
def transfer_wip(order_no: str, p: WipTransfer, request: Request,
                 principal: dict = Depends(require_permission("production.execute"))):
    if p.orderNo != order_no:
        raise HTTPException(409, "orderNo does not match URL")
    with _connect() as conn, conn.cursor() as cur:
        order_id = _order_id(cur, order_no)
        cur.execute("""SELECT COALESCE(SUM(quantity),0) FROM production_inventory_ledger
          WHERE production_order_id=%s AND product_code=%s AND warehouse_code=%s
          AND movement_type IN ('WIP_RECEIPT','WIP_TRANSFER_IN')""", (order_id,p.sku,p.warehouse))
        available = cur.fetchone()[0]
        if available < p.quantity:
            raise HTTPException(409, f"Insufficient WIP: available={available}, requested={p.quantity}")
        cur.execute("""INSERT INTO production_wip_transfers
          (production_order_id,product_code,warehouse_code,quantity,document_no,actor_name,notes)
          VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
          (order_id,p.sku,p.warehouse,p.quantity,p.documentNo,principal["username"],p.notes))
        transfer_id = cur.fetchone()[0]
        cur.execute("""INSERT INTO production_inventory_ledger
          (production_order_id,warehouse_code,movement_type,quantity,unit,reference_no,actor_name,notes)
          VALUES (%s,%s,'WIP_TRANSFER_OUT',%s,'PCS',%s,%s,%s),
                 (%s,%s,'WIP_TRANSFER_IN',%s,'PCS',%s,%s,%s)""",
          (order_id,p.warehouse,p.quantity,p.documentNo,principal["username"],p.fromOperationCode,
           order_id,p.warehouse,p.quantity,p.documentNo,principal["username"],p.toOperationCode))
    return {"documentNo":p.documentNo,"orderNo":order_no,"transferId":transfer_id,"status":"transferred"}


class MaterialConsumption(BaseModel):
    documentNo: str = Field(min_length=1, max_length=100)
    orderNo: str = Field(min_length=1, max_length=100)
    sku: str = Field(min_length=1, max_length=100)
    warehouse: str = Field(default="MAIN", min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    unitCost: Decimal = Field(default=Decimal("0"), ge=0)
    reservationId: int | None = None
    notes: str | None = None


@router.post("/orders/{order_no}/materials/consume", status_code=201)
def consume_material(
    order_no: str,
    p: MaterialConsumption,
    principal: dict = Depends(require_permission("production.execute")),
):
    if p.orderNo != order_no:
        raise HTTPException(409, "orderNo does not match URL")
    with _connect() as conn, conn.cursor() as cur:
        order_id = _order_id(cur, order_no)
        cur.execute(
            """SELECT product_master_id FROM production_orders WHERE id=%s""",
            (order_id,),
        )
        product_master_id = cur.fetchone()[0]
        cur.execute(
            """SELECT id FROM eyt_product_master WHERE sku=%s""",
            (p.sku,),
        )
        component = cur.fetchone()
        if not component:
            raise HTTPException(404, f"Product Master SKU not found: {p.sku}")
        component_product_id = component[0]

        cur.execute(
            """SELECT pg_advisory_xact_lock(hashtext(%s))""",
            (f"{p.sku}:{p.warehouse}",),
        )
        cur.execute(
            """SELECT COALESCE(SUM(
                 CASE WHEN transaction_type IN
                 ('RECEIPT','TRANSFER_IN','RETURN','PRODUCTION_RECEIPT','ADJUSTMENT')
                 THEN quantity ELSE -quantity END),0)
               FROM inventory_transactions
               WHERE product_code=%s AND warehouse_code=%s""",
            (p.sku, p.warehouse),
        )
        on_hand = cur.fetchone()[0]
        if on_hand < p.quantity:
            raise HTTPException(409, f"Insufficient stock: available={on_hand}, requested={p.quantity}")

        if p.reservationId is not None:
            cur.execute(
                """SELECT quantity, status FROM inventory_reservations
                   WHERE id=%s AND product_code=%s AND warehouse_code=%s
                   FOR UPDATE""",
                (p.reservationId, p.sku, p.warehouse),
            )
            reservation = cur.fetchone()
            if not reservation:
                raise HTTPException(404, "Reservation not found")
            if reservation[1] != "RESERVED":
                raise HTTPException(409, "Reservation is not active")
            if reservation[0] < p.quantity:
                raise HTTPException(409, "Consumption exceeds reservation quantity")

        # Resolve valuation from the inventory ledger; client unitCost is only a legacy fallback.
        cur.execute(
            """SELECT COALESCE(SUM(CASE WHEN transaction_type IN
              ('RECEIPT','TRANSFER_IN','PRODUCTION_RECEIPT','RETURN','ADJUSTMENT')
              THEN quantity * unit_cost ELSE 0 END),0)
              / NULLIF(SUM(CASE WHEN transaction_type IN
              ('RECEIPT','TRANSFER_IN','PRODUCTION_RECEIPT','RETURN','ADJUSTMENT')
              THEN quantity ELSE 0 END),0)
              FROM inventory_transactions
              WHERE product_code=%s AND warehouse_code=%s""",
            (p.sku, p.warehouse),
        )
        ledger_cost = cur.fetchone()[0]
        effective_unit_cost = ledger_cost if ledger_cost is not None else p.unitCost

        # Idempotency: repeated document posting returns the existing transaction.
        cur.execute(
            """SELECT id FROM inventory_transactions
               WHERE document_no=%s AND warehouse_code=%s
                 AND product_code=%s AND transaction_type='CONSUMPTION'""",
            (p.documentNo, p.warehouse, p.sku),
        )
        existing = cur.fetchone()
        if existing:
            return {
                "documentNo": p.documentNo,
                "orderNo": order_no,
                "transactionId": existing[0],
                "status": "already_consumed",
                "unitCost": effective_unit_cost,
            }

        cur.execute(
            """INSERT INTO inventory_transactions
               (document_no, warehouse_code, product_code, quantity, unit,
                transaction_type, reference_type, reference_id, unit_cost)
               VALUES (%s,%s,%s,%s,'PCS','CONSUMPTION','PRODUCTION',%s,%s)
               RETURNING id""",
            (p.documentNo, p.warehouse, p.sku, p.quantity, p.orderNo, effective_unit_cost),
        )
        tx_id = cur.fetchone()[0]

        cur.execute(
            """INSERT INTO production_material_movements
               (production_order_id, material_code, warehouse_code, quantity,
                movement_type, document_no, actor_name, notes,
                component_product_id, reservation_id, unit_cost, quantity_source)
               VALUES (%s,%s,%s,%s,'ISSUE',%s,%s,%s,%s,%s,%s,'ACTUAL')
               RETURNING id""",
            (order_id, p.sku, p.warehouse, p.quantity, p.documentNo,
             principal["username"], p.notes, component_product_id,
             p.reservationId, effective_unit_cost),
        )
        movement_id = cur.fetchone()[0]

        if p.reservationId is not None:
            cur.execute(
                """UPDATE inventory_reservations
                   SET quantity = quantity - %s,
                       status = CASE WHEN quantity - %s <= 0 THEN 'CONSUMED' ELSE 'RESERVED' END,
                       consumed_at = CASE WHEN quantity - %s <= 0 THEN CURRENT_TIMESTAMP ELSE consumed_at END
                   WHERE id=%s""",
                (p.quantity, p.quantity, p.quantity, p.reservationId),
            )

    return {
        "documentNo": p.documentNo,
        "orderNo": order_no,
        "transactionId": tx_id,
        "movementId": movement_id,
        "status": "consumed",
        "productMasterId": str(product_master_id) if product_master_id else None,
    }


@router.get("/orders/{order_no}/materials/variance")
def material_variance(
    order_no: str,
    principal: dict = Depends(require_permission("production.read")),
):
    with _connect() as conn, conn.cursor() as cur:
        order_id = _order_id(cur, order_no)
        cur.execute(
            """SELECT product_master_id, target_qty
               FROM production_orders WHERE id=%s""",
            (order_id,),
        )
        product_id, target_qty = cur.fetchone()
        if not product_id:
            raise HTTPException(409, "Production order has no Product Master UUID")
        cur.execute(
            """SELECT b.id, b.yield_factor
               FROM eyt_bom b
               WHERE b.product_id=%s AND b.status='ACTIVE'
               ORDER BY b.version DESC LIMIT 1""",
            (product_id,),
        )
        bom = cur.fetchone()
        if not bom:
            raise HTTPException(404, "Active BOM not found")
        bom_id, yield_factor = bom
        cur.execute(
            """WITH required AS (
                 SELECT bi.component_product_id,
                        p.sku,
                        p.product_name_fa,
                        bi.unit,
                        bi.quantity_per * (1 + bi.scrap_percent / 100.0)
                          * %s / %s AS required_qty
                 FROM eyt_bom_item bi
                 JOIN eyt_product_master p ON p.id=bi.component_product_id
                 WHERE bi.bom_id=%s
               ),
               actual AS (
                 SELECT component_product_id,
                        SUM(CASE WHEN movement_type='ISSUE' THEN quantity
                                 WHEN movement_type='RETURN' THEN -quantity ELSE 0 END) AS actual_qty
                 FROM production_material_movements
                 WHERE production_order_id=%s
                 GROUP BY component_product_id
               )
               SELECT r.component_product_id, r.sku, r.product_name_fa, r.unit,
                      r.required_qty, COALESCE(a.actual_qty,0) AS actual_qty,
                      COALESCE(a.actual_qty,0)-r.required_qty AS variance_qty
               FROM required r
               LEFT JOIN actual a ON a.component_product_id=r.component_product_id
               ORDER BY r.sku""",
            (target_qty, yield_factor, bom_id, order_id),
        )
        rows = cur.fetchall()
        columns = [d.name for d in cur.description]
    return {"orderNo": order_no, "materials": [dict(zip(columns, row)) for row in rows]}
