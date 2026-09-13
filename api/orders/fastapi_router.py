from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import psycopg
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .order_center import CreateOrder, OrderChannel, OrderCenter, OrderLine, PaymentType
from ..production.customer_portal_api import require_customer_session

router = APIRouter(prefix="/api/v1/orders", tags=["Order Center"])


class ItemIn(BaseModel):
    product_id: str
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)


class OrderIn(BaseModel):
    customer_id: str
    warehouse_code: str
    channel: OrderChannel
    items: list[ItemIn] = Field(min_length=1)
    representative_id: str | None = None
    notes: str | None = None
    payment_type: PaymentType = PaymentType.CASH


order_center: OrderCenter | None = None


def configure_order_center(service: OrderCenter) -> None:
    global order_center
    order_center = service


def _resolve_prices(items: list[ItemIn], customer_id: str | None = None) -> list[ItemIn]:
    """Resolve authoritative prices server-side."""
    product_ids = [str(i.product_id) for i in items]
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")

    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, sale_price, is_active FROM products WHERE id=ANY(%s::uuid[])",
            (product_ids,),
        )
        product_rows = {str(r[0]): r for r in cur.fetchall()}
        for pid in product_ids:
            row = product_rows.get(pid)
            if not row or not row[2]:
                raise HTTPException(status_code=422, detail=f"active product not found: {pid}")

        price_rows: dict[str, Decimal] = {}
        if customer_id:
            values_sql = ",".join(["(%s::uuid,%s::numeric)"] * len(items))
            params: list[Any] = []
            for item in items:
                params.extend([str(item.product_id), item.quantity])
            cur.execute(
                f"""WITH requested(product_id, quantity) AS (VALUES {values_sql})
                    SELECT DISTINCT ON (pli.product_id)
                           pli.product_id, pli.unit_price
                    FROM requested r
                    JOIN customers c ON c.id=%s
                    JOIN price_lists pl ON pl.id=c.default_price_list_id
                    JOIN price_list_items pli ON pli.price_list_id=pl.id
                                          AND pli.product_id=r.product_id
                                          AND pli.min_quantity<=r.quantity
                    WHERE pl.active=TRUE AND pli.active=TRUE
                      AND (pl.valid_to IS NULL OR pl.valid_to>CURRENT_TIMESTAMP)
                      AND (pli.valid_to IS NULL OR pli.valid_to>CURRENT_TIMESTAMP)
                      AND pli.valid_from<=CURRENT_TIMESTAMP
                    ORDER BY pli.product_id, pli.min_quantity DESC, pli.valid_from DESC""",
                [*params, customer_id],
            )
            price_rows = {str(r[0]): Decimal(str(r[1])) for r in cur.fetchall()}

        remaining = [pid for pid in product_ids if pid not in price_rows]
        master_rows: dict[str, Decimal] = {}
        if remaining:
            cur.execute(
                """SELECT DISTINCT ON (product_id) product_id, final_price
                   FROM price_master
                   WHERE product_id=ANY(%s::uuid[]) AND status='ACTIVE'
                     AND effective_from<=CURRENT_TIMESTAMP
                     AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP)
                   ORDER BY product_id, effective_from DESC""",
                (remaining,),
            )
            master_rows = {str(r[0]): Decimal(str(r[1] or 0)) for r in cur.fetchall()}

    resolved: list[ItemIn] = []
    for item in items:
        key = str(item.product_id)
        price = price_rows.get(key) or master_rows.get(key)
        if price is None:
            price = Decimal(str(product_rows[key][1] or 0))
        if price <= 0:
            raise HTTPException(status_code=422, detail=f"product has no valid sale price: {item.product_id}")
        resolved.append(item.model_copy(update={"unit_price": price}))
    return resolved


def _require_order_customer(request: Request, order: dict[str, Any]) -> None:
    if order.get("channel") in {OrderChannel.WEBSITE.value, "B2B"}:
        session = require_customer_session(request)
        if session["customerId"] != str(order["customer_id"]):
            raise HTTPException(status_code=403, detail="Customer session does not match order customer")


@router.post("", status_code=201)
def create_order(payload: OrderIn, request: Request, idempotency_key: str | None = Header(default=None)) -> dict[str, Any]:
    if order_center is None:
        raise HTTPException(status_code=503, detail="Order Center is not configured")
    customer_id = payload.customer_id
    if payload.channel.value in {"WEBSITE", "B2B"}:
        session = require_customer_session(request)
        customer_id = session["customerId"]
        if customer_id != payload.customer_id:
            raise HTTPException(status_code=403, detail="Customer session does not match order customer")
    try:
        priced_items = _resolve_prices(payload.items, customer_id=customer_id)
        lines = tuple(
            OrderLine(product_id=i.product_id, quantity=i.quantity, unit_price=i.unit_price or Decimal("0"))
            for i in priced_items
        )
        if any(line.unit_price <= 0 for line in lines):
            raise ValueError("every order line must have a positive unit price")
        return order_center.create(CreateOrder(
            customer_id=customer_id,
            warehouse_code=payload.warehouse_code,
            channel=payload.channel,
            items=lines,
            representative_id=payload.representative_id,
            idempotency_key=idempotency_key,
            notes=payload.notes,
            payment_type=payload.payment_type,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{order_no}")
def get_order(order_no: str, request: Request) -> dict[str, Any]:
    if order_center is None:
        raise HTTPException(status_code=503, detail="Order Center is not configured")
    result = order_center.orders.get(order_no)
    if result is None:
        raise HTTPException(status_code=404, detail="Order not found")
    _require_order_customer(request, result)
    return result


@router.post("/{order_no}/confirm")
def confirm_order(order_no: str, request: Request) -> dict[str, Any]:
    if order_center is None:
        raise HTTPException(status_code=503, detail="Order Center is not configured")
    try:
        order = order_center.orders.get(order_no)
        if order is None:
            raise KeyError(order_no)
        _require_order_customer(request, order)
        return order_center.confirm(order_no)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Order not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
