from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import audit, require_permission

router = APIRouter(prefix="/api/purchase", tags=["purchase-receiving"])


def db():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class SupplierInput(BaseModel):
    supplierCode: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=80)


class PurchaseLine(BaseModel):
    productCode: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    unitPrice: Decimal = Field(ge=0)


class PurchaseOrderInput(BaseModel):
    orderNo: str = Field(min_length=1, max_length=60)
    supplierId: UUID
    warehouseCode: str = Field(min_length=1, max_length=60)
    orderDate: date = Field(default_factory=date.today)
    expectedDate: date | None = None
    prepaymentAmount: Decimal = Field(default=Decimal("0"), ge=0)
    lines: list[PurchaseLine] = Field(min_length=1)


class ReceiptLine(BaseModel):
    productCode: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    unitCost: Decimal | None = Field(default=None, ge=0)


class ReceiptInput(BaseModel):
    receiptNo: str = Field(min_length=1, max_length=60)
    warehouseCode: str = Field(min_length=1, max_length=60)
    lines: list[ReceiptLine] = Field(min_length=1)
    notes: str | None = None


@router.post("/suppliers", status_code=201)
def create_supplier(payload: SupplierInput, request: Request,
                    principal: dict = Depends(require_permission("procurement.write"))):
    with db() as conn:
        try:
            row = conn.execute("INSERT INTO eyt_suppliers(supplier_code,name,phone) VALUES(%s,%s,%s) RETURNING id,supplier_code,name,phone,status", (payload.supplierCode, payload.name, payload.phone)).fetchone()
            conn.commit()
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(409, "Supplier code already exists") from exc
    audit(request, principal, "procurement.supplier.create", row[0], {"supplier_code": row[1]})
    return dict(zip(["id", "supplierCode", "name", "phone", "status"], row))


@router.post("/orders", status_code=201)
def create_order(payload: PurchaseOrderInput, request: Request,
                 principal: dict = Depends(require_permission("procurement.write"))):
    total = money(sum((x.quantity * x.unitPrice for x in payload.lines), Decimal("0")))
    if payload.prepaymentAmount > total:
        raise HTTPException(422, "prepaymentAmount cannot exceed total")
    with db() as conn:
        try:
            supplier = conn.execute("SELECT id FROM eyt_suppliers WHERE id=%s AND status='active'", (payload.supplierId,)).fetchone()
            if not supplier:
                raise HTTPException(422, "Supplier not found or inactive")
            warehouse = conn.execute("SELECT code FROM warehouses WHERE code=%s AND is_active", (payload.warehouseCode,)).fetchone()
            if not warehouse:
                raise HTTPException(422, "Warehouse not found or inactive")
            product_rows = []
            seen = set()
            for line in payload.lines:
                if line.productCode in seen:
                    raise HTTPException(422, "Duplicate productCode in purchase order")
                seen.add(line.productCode)
                product = conn.execute("SELECT id,unit FROM products WHERE product_code=%s AND is_active", (line.productCode,)).fetchone()
                if not product:
                    raise HTTPException(422, f"Product not found or inactive: {line.productCode}")
                product_rows.append((product[0], product[1], line))
            order_id = conn.execute("""INSERT INTO purchase_orders_v1(order_no,supplier_id,warehouse_code,order_date,expected_date,status,total_amount,prepayment_amount,created_by)
                VALUES(%s,%s,%s,%s,%s,'draft',%s,%s,%s) RETURNING id""", (payload.orderNo,payload.supplierId,payload.warehouseCode,payload.orderDate,payload.expectedDate,total,payload.prepaymentAmount,principal["id"])).fetchone()[0]
            for product_id, _, line in product_rows:
                conn.execute("INSERT INTO purchase_order_items_v1(purchase_order_id,product_id,quantity,unit_price) VALUES(%s,%s,%s,%s)", (order_id,product_id,line.quantity,line.unitPrice))
            conn.commit()
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(409, "Purchase order number already exists") from exc
    audit(request, principal, "procurement.order.create", order_id, {"order_no": payload.orderNo, "total": str(total)})
    return {"id": order_id, "orderNo": payload.orderNo, "status": "draft", "totalAmount": total}


@router.post("/orders/{order_no}/approve")
def approve_order(order_no: str, request: Request,
                  principal: dict = Depends(require_permission("procurement.write"))):
    with db() as conn:
        row = conn.execute("UPDATE purchase_orders_v1 SET status='approved',approved_at=now() WHERE order_no=%s AND status='draft' RETURNING id,order_no,status", (order_no,)).fetchone()
        if not row:
            exists = conn.execute("SELECT status FROM purchase_orders_v1 WHERE order_no=%s", (order_no,)).fetchone()
            if not exists:
                raise HTTPException(404, "Purchase order not found")
            raise HTTPException(409, f"Cannot approve order in status {exists[0]}")
        conn.commit()
    audit(request, principal, "procurement.order.approve", row[0], {"order_no": order_no})
    return {"id": row[0], "orderNo": row[1], "status": row[2]}


@router.get("/orders/{order_no}")
def get_order(order_no: str, _=Depends(require_permission("procurement.read"))):
    with db() as conn:
        row = conn.execute("""SELECT o.id,o.order_no,o.supplier_id,s.supplier_code,s.name,o.warehouse_code,o.order_date,o.expected_date,o.status,o.total_amount,o.prepayment_amount
            FROM purchase_orders_v1 o JOIN eyt_suppliers s ON s.id=o.supplier_id WHERE o.order_no=%s""", (order_no,)).fetchone()
        if not row:
            raise HTTPException(404, "Purchase order not found")
        lines = conn.execute("""SELECT i.id,p.product_code,p.name_fa,i.quantity,i.unit_price,
            COALESCE((SELECT SUM(r.quantity) FROM purchase_receipt_items_v1 r WHERE r.purchase_order_item_id=i.id),0) received
            FROM purchase_order_items_v1 i JOIN products p ON p.id=i.product_id WHERE i.purchase_order_id=%s ORDER BY p.product_code""", (row[0],)).fetchall()
    result = dict(zip(["id","orderNo","supplierId","supplierCode","supplierName","warehouseCode","orderDate","expectedDate","status","totalAmount","prepaymentAmount"], row))
    result["lines"] = [{"id": x[0],"productCode":x[1],"productName":x[2],"orderedQty":x[3],"unitPrice":x[4],"receivedQty":x[5],"remainingQty":x[3]-x[5]} for x in lines]
    return result


@router.post("/orders/{order_no}/receive", status_code=201)
def receive_order(order_no: str, payload: ReceiptInput, request: Request,
                  principal: dict = Depends(require_permission("procurement.receive"))):
    with db() as conn:
        order = conn.execute("SELECT id,status,warehouse_code FROM purchase_orders_v1 WHERE order_no=%s FOR UPDATE", (order_no,)).fetchone()
        if not order:
            raise HTTPException(404, "Purchase order not found")
        if order[1] not in ("approved", "partially_received"):
            raise HTTPException(409, f"Cannot receive order in status {order[1]}")
        if payload.warehouseCode != order[2]:
            raise HTTPException(422, "Receipt warehouse must match purchase order warehouse")
        warehouse = conn.execute("SELECT code FROM warehouses WHERE code=%s AND is_active", (payload.warehouseCode,)).fetchone()
        if not warehouse:
            raise HTTPException(422, "Warehouse not found or inactive")
        if conn.execute("SELECT 1 FROM purchase_receipts_v1 WHERE receipt_no=%s", (payload.receiptNo,)).fetchone():
            raise HTTPException(409, "Receipt number already exists")
        items = {}
        for line in payload.lines:
            if line.productCode in items:
                raise HTTPException(422, "Duplicate productCode in receipt")
            item = conn.execute("""SELECT i.id,i.product_id,i.quantity,i.unit_price,p.product_code
                FROM purchase_order_items_v1 i JOIN products p ON p.id=i.product_id
                WHERE i.purchase_order_id=%s AND p.product_code=%s FOR UPDATE""", (order[0],line.productCode)).fetchone()
            if not item:
                raise HTTPException(422, f"Product is not on purchase order: {line.productCode}")
            received = conn.execute("SELECT COALESCE(SUM(quantity),0) FROM purchase_receipt_items_v1 WHERE purchase_order_item_id=%s", (item[0],)).fetchone()[0]
            if received + line.quantity > item[2]:
                raise HTTPException(409, f"Over-receipt for {line.productCode}: ordered={item[2]} already_received={received}")
            items[line.productCode] = (item, line, received)
        receipt_id = conn.execute("INSERT INTO purchase_receipts_v1(receipt_no,purchase_order_id,warehouse_code,received_by,notes) VALUES(%s,%s,%s,%s,%s) RETURNING id", (payload.receiptNo,order[0],payload.warehouseCode,principal["id"],payload.notes)).fetchone()[0]
        for code,(item,line,_) in items.items():
            cost = line.unitCost if line.unitCost is not None else item[3]
            conn.execute("INSERT INTO purchase_receipt_items_v1(receipt_id,purchase_order_item_id,product_id,quantity,unit_cost) VALUES(%s,%s,%s,%s,%s)", (receipt_id,item[0],item[1],line.quantity,cost))
            conn.execute("INSERT INTO inventory_transactions(product_code,warehouse_code,quantity,unit,transaction_type,reference_type,reference_id,unit_cost) VALUES(%s,%s,%s,%s,'RECEIPT','PURCHASE_RECEIPT',%s,%s)", (code,payload.warehouseCode,line.quantity,"PCS",payload.receiptNo,cost))
        totals = conn.execute("""SELECT COUNT(*) FILTER (WHERE x.received < x.ordered), COUNT(*) FILTER (WHERE x.received >= x.ordered)
            FROM (SELECT i.quantity ordered,COALESCE((SELECT SUM(r.quantity) FROM purchase_receipt_items_v1 r WHERE r.purchase_order_item_id=i.id),0) received FROM purchase_order_items_v1 i WHERE i.purchase_order_id=%s) x""", (order[0],)).fetchone()
        new_status = "partially_received" if totals[0] else "received"
        conn.execute("UPDATE purchase_orders_v1 SET status=%s WHERE id=%s", (new_status,order[0]))
        conn.commit()
    audit(request, principal, "procurement.order.receive", order[0], {"order_no": order_no, "receipt_no": payload.receiptNo, "line_count": len(payload.lines)})
    return {"id": receipt_id, "receiptNo": payload.receiptNo, "orderNo": order_no, "status": new_status}


@router.get("/orders/{order_no}/receipts")
def list_receipts(order_no: str, _=Depends(require_permission("procurement.read"))):
    with db() as conn:
        order = conn.execute("SELECT id FROM purchase_orders_v1 WHERE order_no=%s", (order_no,)).fetchone()
        if not order:
            raise HTTPException(404, "Purchase order not found")
        rows = conn.execute("""SELECT r.id,r.receipt_no,r.warehouse_code,r.received_at,r.notes,
            COALESCE(json_agg(json_build_object('productCode',p.product_code,'quantity',ri.quantity,'unitCost',ri.unit_cost)),'[]')
            FROM purchase_receipts_v1 r JOIN purchase_receipt_items_v1 ri ON ri.receipt_id=r.id JOIN products p ON p.id=ri.product_id
            WHERE r.purchase_order_id=%s GROUP BY r.id ORDER BY r.received_at""", (order[0],)).fetchall()
    return [{"id":r[0],"receiptNo":r[1],"warehouseCode":r[2],"receivedAt":r[3],"notes":r[4],"lines":r[5]} for r in rows]
