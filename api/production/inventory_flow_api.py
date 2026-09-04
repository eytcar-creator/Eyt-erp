"""Real PostgreSQL inventory flows used by the production portal."""
from decimal import Decimal
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg.types.json import Json

from .auth import require_permission

router = APIRouter(prefix="/api/inventory", tags=["inventory-flow"])


class StockLine(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    unitCost: Decimal = Field(default=Decimal("0"), ge=0)


class StockFlow(BaseModel):
    documentNo: str = Field(min_length=1, max_length=100)
    warehouse: str = Field(min_length=1, max_length=100)
    lines: list[StockLine] = Field(min_length=1)
    referenceType: str | None = None
    referenceId: str | None = None


class StockBalance(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    warehouse: str = Field(min_length=1, max_length=100)


def _connect():
    import psycopg
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    return psycopg.connect(url)


def _lock_key(sku: str, warehouse: str) -> str:
    return f"{sku}:{warehouse}"


def _on_hand(cur, sku: str, warehouse: str) -> Decimal:
    cur.execute(
        """SELECT COALESCE(SUM(CASE WHEN transaction_type IN
        ('RECEIPT','TRANSFER_IN','RETURN','PRODUCTION_RECEIPT','ADJUSTMENT')
        THEN quantity ELSE -quantity END),0)
        FROM inventory_transactions
        WHERE product_code=%s AND warehouse_code=%s""",
        (sku, warehouse),
    )
    return cur.fetchone()[0]


def _reserved(cur, sku: str, warehouse: str) -> Decimal:
    cur.execute(
        """SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations
        WHERE product_code=%s AND warehouse_code=%s AND status='RESERVED'""",
        (sku, warehouse),
    )
    return cur.fetchone()[0]


def _audit(cur, principal: dict, request: Request, action: str, document_no: str, metadata: dict):
    cur.execute(
        """INSERT INTO eyt_audit_logs
        (actor_user_id, action, entity_id, correlation_id, ip_address, metadata)
        VALUES (%s,%s,NULL,%s,%s,%s)""",
        (principal["id"], action, request.headers.get("X-Correlation-ID") or document_no,
         request.client.host if request.client else None, Json(metadata)),
    )


def _post_transaction(cur, payload: StockFlow, line: StockLine, transaction_type: str):
    cur.execute(
        """INSERT INTO inventory_transactions
        (document_no, warehouse_code, product_code, quantity, unit,
         transaction_type, reference_type, reference_id, unit_cost)
        VALUES (%s,%s,%s,%s,'PCS',%s,%s,%s,%s)
        RETURNING id, created_at""",
        (payload.documentNo, payload.warehouse, line.sku, line.quantity,
         transaction_type, payload.referenceType, payload.referenceId, line.unitCost),
    )
    return cur.fetchone()


@router.post("/receive", status_code=201)
def receive(payload: StockFlow, request: Request,
            principal: dict = Depends(require_permission("inventory.write"))):
    with _connect() as conn, conn.cursor() as cur:
        for line in payload.lines:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (_lock_key(line.sku, payload.warehouse),))
            row = _post_transaction(cur, payload, line, "RECEIPT")
            _audit(cur, principal, request, "inventory.receive", payload.documentNo,
                   {"sku": line.sku, "quantity": str(line.quantity), "warehouse": payload.warehouse, "transactionId": row[0]})
    return {"documentNo": payload.documentNo, "warehouse": payload.warehouse, "status": "received", "lines": [x.model_dump() for x in payload.lines]}


@router.post("/reserve", status_code=201)
def reserve(payload: StockFlow, request: Request,
            principal: dict = Depends(require_permission("inventory.write"))):
    with _connect() as conn, conn.cursor() as cur:
        for line in payload.lines:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (_lock_key(line.sku, payload.warehouse),))
            available = _on_hand(cur, line.sku, payload.warehouse) - _reserved(cur, line.sku, payload.warehouse)
            if available < line.quantity:
                raise HTTPException(status_code=409, detail=f"Insufficient available inventory for {line.sku}: available={available}, requested={line.quantity}")
            cur.execute(
                """INSERT INTO inventory_reservations
                (document_no, warehouse_code, product_code, quantity, status, reference_type, reference_id)
                VALUES (%s,%s,%s,%s,'RESERVED',%s,%s) RETURNING id""",
                (payload.documentNo, payload.warehouse, line.sku, line.quantity, payload.referenceType, payload.referenceId),
            )
            reservation_id = cur.fetchone()[0]
            _audit(cur, principal, request, "inventory.reserve", payload.documentNo,
                   {"sku": line.sku, "quantity": str(line.quantity), "warehouse": payload.warehouse, "reservationId": reservation_id})
    return {"documentNo": payload.documentNo, "warehouse": payload.warehouse, "status": "reserved", "lines": [x.model_dump() for x in payload.lines]}


@router.post("/issue", status_code=201)
def issue(payload: StockFlow, request: Request,
           principal: dict = Depends(require_permission("inventory.write"))):
    with _connect() as conn, conn.cursor() as cur:
        for line in payload.lines:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (_lock_key(line.sku, payload.warehouse),))
            available = _on_hand(cur, line.sku, payload.warehouse) - _reserved(cur, line.sku, payload.warehouse)
            cur.execute(
                """SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations
                WHERE product_code=%s AND warehouse_code=%s AND document_no=%s AND status='RESERVED'""",
                (line.sku, payload.warehouse, payload.documentNo),
            )
            document_reserved = cur.fetchone()[0]
            if available + document_reserved < line.quantity:
                raise HTTPException(status_code=409, detail=f"Insufficient stock for issue {line.sku}: available={available}, reservedForDocument={document_reserved}, requested={line.quantity}")
            row = _post_transaction(cur, payload, line, "ISSUE")
            remaining = line.quantity
            cur.execute(
                """SELECT id, quantity FROM inventory_reservations
                WHERE product_code=%s AND warehouse_code=%s AND document_no=%s AND status='RESERVED'
                ORDER BY created_at, id FOR UPDATE""",
                (line.sku, payload.warehouse, payload.documentNo),
            )
            for reservation_id, reservation_qty in cur.fetchall():
                if remaining <= 0:
                    break
                consumed = min(remaining, reservation_qty)
                if consumed == reservation_qty:
                    cur.execute("UPDATE inventory_reservations SET status='CONSUMED', consumed_at=CURRENT_TIMESTAMP WHERE id=%s", (reservation_id,))
                else:
                    cur.execute("UPDATE inventory_reservations SET quantity=quantity-%s WHERE id=%s", (consumed, reservation_id))
                remaining -= consumed
            _audit(cur, principal, request, "inventory.issue", payload.documentNo,
                   {"sku": line.sku, "quantity": str(line.quantity), "warehouse": payload.warehouse, "transactionId": row[0]})
    return {"documentNo": payload.documentNo, "warehouse": payload.warehouse, "status": "issued", "lines": [x.model_dump() for x in payload.lines]}


@router.post("/fg-receipt", status_code=201)
def fg_receipt(payload: StockFlow, request: Request,
               principal: dict = Depends(require_permission("inventory.write"))):
    with _connect() as conn, conn.cursor() as cur:
        for line in payload.lines:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (_lock_key(line.sku, payload.warehouse),))
            row = _post_transaction(cur, payload, line, "PRODUCTION_RECEIPT")
            _audit(cur, principal, request, "inventory.fg_receipt", payload.documentNo,
                   {"sku": line.sku, "quantity": str(line.quantity), "warehouse": payload.warehouse, "transactionId": row[0]})
    return {"documentNo": payload.documentNo, "warehouse": payload.warehouse, "status": "fg_received", "lines": [x.model_dump() for x in payload.lines]}


@router.get("/balance/{sku}/{warehouse}")
def balance(sku: str, warehouse: str, _=Depends(require_permission("inventory.read"))):
    with _connect() as conn, conn.cursor() as cur:
        on_hand = _on_hand(cur, sku, warehouse)
        reserved = _reserved(cur, sku, warehouse)
    return {"sku": sku, "warehouse": warehouse, "onHand": on_hand, "reserved": reserved, "available": on_hand - reserved}


@router.post("/balance/check")
def check_balance(payload: StockBalance, _=Depends(require_permission("inventory.read"))):
    with _connect() as conn, conn.cursor() as cur:
        on_hand = _on_hand(cur, payload.sku, payload.warehouse)
        reserved = _reserved(cur, payload.sku, payload.warehouse)
    return {"sku": payload.sku, "warehouse": payload.warehouse, "onHand": on_hand, "reserved": reserved, "available": on_hand - reserved}
