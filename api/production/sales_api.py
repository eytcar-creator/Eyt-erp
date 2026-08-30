from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import audit, require_permission

router = APIRouter(prefix="/api/sales", tags=["sales"])


def db():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class CustomerInput(BaseModel):
    customerCode: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=80)
    taxId: str | None = Field(default=None, max_length=80)
    address: str | None = None
    creditLimit: Decimal = Field(default=Decimal("0"), ge=0)


class SalesLine(BaseModel):
    productCode: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    unitPrice: Decimal = Field(ge=0)


class SalesOrder(BaseModel):
    orderNo: str = Field(min_length=1, max_length=60)
    customerCode: str = Field(min_length=1, max_length=60)
    warehouseCode: str = Field(min_length=1, max_length=60)
    orderDate: date = Field(default_factory=date.today)
    lines: list[SalesLine] = Field(min_length=1)
    prepayment: Decimal = Field(default=Decimal("0"), ge=0)


class InvoiceInput(BaseModel):
    invoiceNo: str = Field(min_length=1, max_length=60)


class PaymentInput(BaseModel):
    amount: Decimal = Field(gt=0)
    paymentDate: date = Field(default_factory=date.today)
    paymentMethod: str | None = Field(default=None, max_length=40)
    referenceNo: str | None = Field(default=None, max_length=100)
    invoiceNo: str


@router.post("/customers", status_code=201)
def create_customer(payload: CustomerInput, request: Request,
                    principal: dict = Depends(require_permission("sales.write"))):
    with db() as conn:
        try:
            row = conn.execute(
                """INSERT INTO customers(customer_code,name,phone,tax_id,address,credit_limit)
                   VALUES(%s,%s,%s,%s,%s,%s)
                   RETURNING id,customer_code,name,phone,tax_id,address,credit_limit,is_active""",
                (payload.customerCode, payload.name, payload.phone, payload.taxId,
                 payload.address, payload.creditLimit),
            ).fetchone()
            conn.commit()
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(409, "Customer code already exists") from exc
    audit(request, principal, "sales.customer.create", row[0], {"customer_code": row[1]})
    return dict(zip(["id","customerCode","name","phone","taxId","address","creditLimit","isActive"], row))


@router.post("/orders", status_code=201)
def create_order(payload: SalesOrder, request: Request,
                 principal: dict = Depends(require_permission("sales.write"))):
    with db() as conn:
        customer = conn.execute(
            "SELECT id,credit_limit FROM customers WHERE customer_code=%s AND is_active",
            (payload.customerCode,),
        ).fetchone()
        if not customer:
            raise HTTPException(422, "Customer not found or inactive")
        warehouse = conn.execute(
            "SELECT code FROM warehouses WHERE code=%s AND is_active",
            (payload.warehouseCode,),
        ).fetchone()
        if not warehouse:
            raise HTTPException(422, "Warehouse not found or inactive")

        product_rows = []
        seen: set[str] = set()
        subtotal = Decimal("0")
        for line in payload.lines:
            if line.productCode in seen:
                raise HTTPException(422, "Duplicate productCode in sales order")
            seen.add(line.productCode)
            product = conn.execute(
                "SELECT id,purchase_price,sale_price FROM products WHERE product_code=%s AND is_active",
                (line.productCode,),
            ).fetchone()
            if not product:
                raise HTTPException(422, f"Product not found or inactive: {line.productCode}")
            unit_price = line.unitPrice
            unit_cost = product[1]
            subtotal += line.quantity * unit_price
            product_rows.append((product[0], line, unit_cost))
        subtotal = money(subtotal)
        if payload.prepayment > subtotal:
            raise HTTPException(422, "prepayment cannot exceed order total")

        try:
            order_id = conn.execute(
                """INSERT INTO sales_orders(order_no,customer_id,warehouse_code,order_date,status,subtotal,prepayment_amount,created_by)
                   VALUES(%s,%s,%s,%s,'DRAFT',%s,%s,%s) RETURNING id""",
                (payload.orderNo, customer[0], payload.warehouseCode, payload.orderDate,
                 subtotal, payload.prepayment, principal["id"]),
            ).fetchone()[0]
            for product_id, line, unit_cost in product_rows:
                conn.execute(
                    """INSERT INTO sales_order_items(sales_order_id,product_id,quantity,unit_price,unit_cost)
                       VALUES(%s,%s,%s,%s,%s)""",
                    (order_id, product_id, line.quantity, line.unitPrice, unit_cost),
                )
            conn.commit()
        except psycopg.errors.UniqueViolation as exc:
            conn.rollback()
            raise HTTPException(409, "Sales order number already exists") from exc
    audit(request, principal, "sales.order.create", order_id, {"order_no": payload.orderNo, "total": str(subtotal)})
    return {"id": order_id, "orderNo": payload.orderNo, "status": "DRAFT", "subtotal": subtotal, "prepayment": payload.prepayment}


@router.post("/orders/{order_no}/confirm")
def confirm_order(order_no: str, request: Request,
                  principal: dict = Depends(require_permission("sales.write"))):
    with db() as conn:
        row = conn.execute(
            "UPDATE sales_orders SET status='CONFIRMED' WHERE order_no=%s AND status='DRAFT' RETURNING id,order_no,status,subtotal,prepayment_amount",
            (order_no,),
        ).fetchone()
        if not row:
            exists = conn.execute("SELECT status FROM sales_orders WHERE order_no=%s", (order_no,)).fetchone()
            if not exists:
                raise HTTPException(404, "Sales order not found")
            raise HTTPException(409, f"Cannot confirm order in status {exists[0]}")
        conn.commit()
    audit(request, principal, "sales.order.confirm", row[0], {"order_no": order_no})
    return {"id": row[0], "orderNo": row[1], "status": row[2], "subtotal": row[3], "prepayment": row[4]}


@router.post("/orders/{order_no}/invoice", status_code=201)
def issue_invoice(order_no: str, payload: InvoiceInput, request: Request,
                  principal: dict = Depends(require_permission("sales.write"))):
    with db() as conn:
        order = conn.execute(
            "SELECT id,customer_id,status,subtotal,prepayment_amount FROM sales_orders WHERE order_no=%s FOR UPDATE",
            (order_no,),
        ).fetchone()
        if not order:
            raise HTTPException(404, "Sales order not found")
        if order[2] not in ("CONFIRMED", "FULFILLED"):
            raise HTTPException(409, f"Cannot invoice order in status {order[2]}")
        try:
            invoice_id = conn.execute(
                """INSERT INTO invoices(invoice_no,sales_order_id,customer_id,subtotal,prepayment_amount,receivable_amount)
                   VALUES(%s,%s,%s,%s,%s,%s) RETURNING id,invoice_no,subtotal,prepayment_amount,receivable_amount,status""",
                (payload.invoiceNo, order[0], order[1], order[3], order[4], order[3] - order[4]),
            ).fetchone()
            conn.commit()
        except psycopg.errors.UniqueViolation as exc:
            conn.rollback()
            raise HTTPException(409, "Invoice number already exists or order is already invoiced") from exc
    audit(request, principal, "sales.invoice.issue", invoice_id[0], {"invoice_no": payload.invoiceNo, "order_no": order_no})
    return dict(zip(["id","invoiceNo","subtotal","prepayment","receivable","status"], invoice_id))


@router.post("/orders/{order_no}/fulfill")
def fulfill_order(order_no: str, request: Request,
                  principal: dict = Depends(require_permission("sales.fulfill"))):
    with db() as conn:
        order = conn.execute(
            "SELECT id,customer_id,warehouse_code,status FROM sales_orders WHERE order_no=%s FOR UPDATE",
            (order_no,),
        ).fetchone()
        if not order:
            raise HTTPException(404, "Sales order not found")
        if order[3] != "CONFIRMED":
            raise HTTPException(409, f"Cannot fulfill order in status {order[3]}")

        lines = conn.execute(
            """SELECT i.product_id,p.product_code,i.quantity,i.unit_cost
               FROM sales_order_items i JOIN products p ON p.id=i.product_id
               WHERE i.sales_order_id=%s ORDER BY p.product_code""",
            (order[0],),
        ).fetchall()
        for product_id, product_code, quantity, unit_cost in lines:
            balance = conn.execute(
                """SELECT COALESCE(SUM(CASE
                    WHEN transaction_type IN ('RECEIPT','TRANSFER_IN','RETURN','PRODUCTION_RECEIPT','ADJUSTMENT') THEN quantity
                    ELSE -quantity END),0)
                   FROM inventory_transactions
                   WHERE product_code=%s AND warehouse_code=%s""",
                (product_code, order[2]),
            ).fetchone()[0]
            reserved = conn.execute(
                """SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations
                   WHERE product_code=%s AND warehouse_code=%s AND status='RESERVED'""",
                (product_code, order[2]),
            ).fetchone()[0]
            available = balance - reserved
            if available < quantity:
                raise HTTPException(409, f"Insufficient available inventory for {product_code}: available={available} required={quantity}")

            released = conn.execute(
                """SELECT COALESCE(SUM(quantity-consumed_qty),0)
                   FROM finished_goods_releases
                   WHERE product_code=%s AND warehouse_code=%s AND release_status='RELEASED'""",
                (product_code, order[2]),
            ).fetchone()[0]
            if released < quantity:
                raise HTTPException(409, f"QC release required for {product_code}: releasable={released} required={quantity}")

        for _, product_code, quantity, unit_cost in lines:
            conn.execute(
                """INSERT INTO inventory_transactions
                   (product_code,warehouse_code,quantity,unit,transaction_type,reference_type,reference_id,unit_cost)
                   VALUES(%s,%s,%s,'PCS','ISSUE','SALES_ORDER',%s,%s)""",
                (product_code, order[2], quantity, order_no, unit_cost),
            )
            remaining = quantity
            releases = conn.execute(
                """SELECT id,quantity-consumed_qty FROM finished_goods_releases
                   WHERE product_code=%s AND warehouse_code=%s AND release_status='RELEASED' AND quantity>consumed_qty
                   ORDER BY released_at,id FOR UPDATE""",
                (product_code, order[2]),
            ).fetchall()
            for release_id, releasable in releases:
                take = min(remaining, releasable)
                conn.execute("UPDATE finished_goods_releases SET consumed_qty=consumed_qty+%s WHERE id=%s", (take, release_id))
                conn.execute(
                    """INSERT INTO traceability_events
                       (batch_no,product_code,event_type,reference_type,reference_id,actor,notes)
                       SELECT qb.batch_no,%s,'SHIPMENT','SALES_ORDER',%s,%s,'Finished goods shipped'
                       FROM quality_batches qb JOIN finished_goods_releases fgr ON fgr.quality_batch_id=qb.id
                       WHERE fgr.id=%s""",
                    (product_code, order_no, principal["username"], release_id),
                )
                remaining -= take
                if remaining <= 0:
                    break
        conn.execute("UPDATE sales_orders SET status='FULFILLED' WHERE id=%s", (order[0],))
        conn.commit()

    audit(request, principal, "sales.order.fulfill", order[0], {"order_no": order_no})
    return {"orderNo": order_no, "status": "FULFILLED"}


@router.post("/payments", status_code=201)
def record_payment(payload: PaymentInput, request: Request,
                   principal: dict = Depends(require_permission("finance.write"))):
    with db() as conn:
        invoice = conn.execute(
            "SELECT id,customer_id,receivable_amount,status FROM invoices WHERE invoice_no=%s FOR UPDATE",
            (payload.invoiceNo,),
        ).fetchone()
        if not invoice or invoice[3] == "VOID":
            raise HTTPException(404, "Invoice not found or void")
        if payload.amount > invoice[2]:
            raise HTTPException(409, "Payment exceeds outstanding invoice balance")
        payment_id = conn.execute(
            """INSERT INTO payments(customer_id,payment_date,amount,payment_method,reference_no)
               VALUES(%s,%s,%s,%s,%s) RETURNING id""",
            (invoice[1], payload.paymentDate, payload.amount, payload.paymentMethod, payload.referenceNo),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO payment_allocations(payment_id,invoice_id,amount) VALUES(%s,%s,%s)",
            (payment_id, invoice[0], payload.amount),
        )
        new_receivable = invoice[2] - payload.amount
        new_status = "PAID" if new_receivable == 0 else "PARTIALLY_PAID"
        conn.execute(
            "UPDATE invoices SET receivable_amount=%s,status=%s WHERE id=%s",
            (new_receivable, new_status, invoice[0]),
        )
        conn.commit()
    audit(request, principal, "finance.payment.record", payment_id, {"invoice_no": payload.invoiceNo, "amount": str(payload.amount)})
    return {"paymentId": payment_id, "invoiceNo": payload.invoiceNo, "allocated": payload.amount, "remainingReceivable": new_receivable, "invoiceStatus": new_status}


@router.get("/orders/{order_no}")
def get_order(order_no: str, _=Depends(require_permission("sales.read"))):
    with db() as conn:
        order = conn.execute(
            """SELECT o.id,o.order_no,c.customer_code,c.name,o.warehouse_code,o.order_date,o.status,o.subtotal,o.prepayment_amount
               FROM sales_orders o JOIN customers c ON c.id=o.customer_id WHERE o.order_no=%s""",
            (order_no,),
        ).fetchone()
        if not order:
            raise HTTPException(404, "Sales order not found")
        lines = conn.execute(
            """SELECT p.product_code,p.name_fa,i.quantity,i.unit_price,i.unit_cost
               FROM sales_order_items i JOIN products p ON p.id=i.product_id WHERE i.sales_order_id=%s ORDER BY p.product_code""",
            (order[0],),
        ).fetchall()
        invoice = conn.execute(
            "SELECT invoice_no,subtotal,prepayment_amount,receivable_amount,status FROM invoices WHERE sales_order_id=%s",
            (order[0],),
        ).fetchone()
    result = dict(zip(["id","orderNo","customerCode","customerName","warehouseCode","orderDate","status","subtotal","prepayment"], order))
    result["lines"] = [dict(zip(["productCode","productName","quantity","unitPrice","unitCost"], row)) for row in lines]
    result["invoice"] = None if invoice is None else dict(zip(["invoiceNo","subtotal","prepayment","receivable","status"], invoice))
    return result


@router.post("/quote")
def quote(payload: SalesOrder, _=Depends(require_permission("sales.write"))):
    subtotal = sum((x.quantity * x.unitPrice for x in payload.lines), Decimal("0"))
    balance = max(Decimal("0"), subtotal - payload.prepayment)
    return {"customerCode": payload.customerCode, "subtotal": money(subtotal), "prepayment": payload.prepayment, "balance_due": money(balance)}
