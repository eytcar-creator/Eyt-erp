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
