from __future__ import annotations

from decimal import Decimal
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_permission

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

POSITIVE_TYPES = {"RECEIPT", "TRANSFER_IN", "RETURN", "PRODUCTION_RECEIPT", "ADJUSTMENT"}
NEGATIVE_TYPES = {"ISSUE", "TRANSFER_OUT", "CONSUMPTION", "SCRAP"}
ALL_TYPES = POSITIVE_TYPES | NEGATIVE_TYPES


class TransactionInput(BaseModel):
    productCode: str = Field(min_length=1, max_length=100)
    warehouseCode: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    unit: str = "PCS"
    transactionType: str
    referenceType: str | None = None
    referenceId: str | None = None
    unitCost: Decimal = Field(default=Decimal("0"), ge=0)


class ReservationInput(BaseModel):
    productCode: str = Field(min_length=1, max_length=100)
    warehouseCode: str = Field(min_length=1, max_length=100)
    referenceType: str = Field(min_length=1, max_length=50)
    referenceId: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)


class BomItemInput(BaseModel):
    componentCode: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    unit: str = "PCS"
    scrapPercent: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class BomInput(BaseModel):
    bomCode: str = Field(min_length=1, max_length=100)
    productCode: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=30)
    status: str = "DRAFT"
    items: list[BomItemInput] = []


def _connect():
    import psycopg
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    return psycopg.connect(url)


def _signed_case() -> str:
    return "CASE WHEN transaction_type IN ('RECEIPT','TRANSFER_IN','RETURN','PRODUCTION_RECEIPT','ADJUSTMENT') THEN quantity ELSE -quantity END"


@router.get("/balance/{product_code}/{warehouse_code}")
def balance(product_code: str, warehouse_code: str, _=Depends(require_permission("inventory.read"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COALESCE(SUM({_signed_case()}),0) FROM inventory_transactions WHERE product_code=%s AND warehouse_code=%s", (product_code, warehouse_code))
        on_hand = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations WHERE product_code=%s AND warehouse_code=%s AND status='RESERVED'", (product_code, warehouse_code))
        reserved = cur.fetchone()[0]
    return {"productCode": product_code, "warehouseCode": warehouse_code, "onHand": on_hand, "reserved": reserved, "available": on_hand - reserved}


@router.post("/transactions", status_code=201)
def create_transaction(payload: TransactionInput, _=Depends(require_permission("inventory.execute"))):
    tx_type = payload.transactionType.upper()
    if tx_type not in ALL_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported transaction type")
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COALESCE(SUM({_signed_case()}),0) FROM inventory_transactions WHERE product_code=%s AND warehouse_code=%s FOR UPDATE", (payload.productCode, payload.warehouseCode))
        current = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations WHERE product_code=%s AND warehouse_code=%s AND status='RESERVED'", (payload.productCode, payload.warehouseCode))
        reserved = cur.fetchone()[0]
        if tx_type in NEGATIVE_TYPES and current - reserved < payload.quantity:
            raise HTTPException(status_code=409, detail="Insufficient available inventory")
        cur.execute("""INSERT INTO inventory_transactions
            (product_code, warehouse_code, quantity, unit, transaction_type, reference_type, reference_id, unit_cost)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id, created_at""",
            (payload.productCode, payload.warehouseCode, payload.quantity, payload.unit, tx_type, payload.referenceType, payload.referenceId, payload.unitCost))
        row = cur.fetchone()
    return {"id": row[0], "createdAt": row[1], "transactionType": tx_type}


@router.post("/reservations", status_code=201)
def reserve(payload: ReservationInput, _=Depends(require_permission("inventory.execute"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COALESCE(SUM({_signed_case()}),0) FROM inventory_transactions WHERE product_code=%s AND warehouse_code=%s", (payload.productCode, payload.warehouseCode))
        on_hand = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations WHERE product_code=%s AND warehouse_code=%s AND status='RESERVED'", (payload.productCode, payload.warehouseCode))
        reserved = cur.fetchone()[0]
        if on_hand - reserved < payload.quantity:
            raise HTTPException(status_code=409, detail="Insufficient available inventory for reservation")
        cur.execute("""INSERT INTO inventory_reservations
            (product_code, warehouse_code, reference_type, reference_id, quantity)
            VALUES (%s,%s,%s,%s,%s) RETURNING id, created_at""",
            (payload.productCode, payload.warehouseCode, payload.referenceType, payload.referenceId, payload.quantity))
        row = cur.fetchone()
    return {"id": row[0], "status": "RESERVED", "createdAt": row[1]}


@router.post("/reservations/{reservation_id}/release")
def release_reservation(reservation_id: int, _=Depends(require_permission("inventory.execute"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("UPDATE inventory_reservations SET status='RELEASED' WHERE id=%s AND status='RESERVED' RETURNING id", (reservation_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Active reservation not found")
    return {"id": row[0], "status": "RELEASED"}


@router.post("/boms", status_code=201)
def create_bom(payload: BomInput, _=Depends(require_permission("production.execute"))):
    if payload.status not in {"DRAFT", "ACTIVE", "OBSOLETE"}:
        raise HTTPException(status_code=422, detail="Invalid BOM status")
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO bom_versions (bom_code, product_code, version, status) VALUES (%s,%s,%s,%s) RETURNING id", (payload.bomCode, payload.productCode, payload.version, payload.status))
        bom_id = cur.fetchone()[0]
        for item in payload.items:
            cur.execute("INSERT INTO bom_items (bom_version_id, component_code, quantity, unit, scrap_percent) VALUES (%s,%s,%s,%s,%s)", (bom_id, item.componentCode, item.quantity, item.unit, item.scrapPercent))
    return {"id": bom_id, "bomCode": payload.bomCode, "version": payload.version, "status": payload.status, "itemCount": len(payload.items)}


@router.get("/boms/{bom_code}/{version}")
def get_bom(bom_code: str, version: str, _=Depends(require_permission("production.read"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, product_code, status, effective_from FROM bom_versions WHERE bom_code=%s AND version=%s", (bom_code, version))
        bom = cur.fetchone()
        if bom is None:
            raise HTTPException(status_code=404, detail="BOM version not found")
        cur.execute("SELECT component_code, quantity, unit, scrap_percent FROM bom_items WHERE bom_version_id=%s ORDER BY id", (bom[0],))
        items = [{"componentCode": r[0], "quantity": r[1], "unit": r[2], "scrapPercent": r[3]} for r in cur.fetchall()]
    return {"id": bom[0], "bomCode": bom_code, "version": version, "productCode": bom[1], "status": bom[2], "effectiveFrom": bom[3], "items": items}


@router.get("/costing/{order_no}")
def costing(order_no: str, _=Depends(require_permission("production.read"))):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT material_cost, operation_cost, contractor_cost, scrap_cost, direct_cost, total_cost, updated_at FROM production_costs WHERE production_order_no=%s", (order_no,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Production costing not found")
    return {"orderNo": order_no, "materialCost": row[0], "operationCost": row[1], "contractorCost": row[2], "scrapCost": row[3], "directCost": row[4], "totalCost": row[5], "updatedAt": row[6]}
