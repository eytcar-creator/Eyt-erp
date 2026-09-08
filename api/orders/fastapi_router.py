from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import psycopg
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .order_center import CreateOrder, OrderChannel, OrderCenter, OrderLine
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


order_center: OrderCenter | None = None


def configure_order_center(service: OrderCenter) -> None:
    global order_center
    order_center = service


def _resolve_prices(items: list[ItemIn], customer_id: str | None = None) -> list[ItemIn]:
    """Resolve prices in order: customer price list, price master, product sale price."""
    unresolved = [i.product_id for i in items if i.unit_price is None or i.unit_price <= 0]
    if not unresolved:
        return items
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        price_rows = {}
        if customer_id:
            cur.execute(
                """SELECT pli.product_id, pli.unit_price
                   FROM customers c
                   JOIN price_lists pl ON pl.id=c.default_price_list_id
                   JOIN price_list_items pli ON pli.price_list_id=pl.id
                   WHERE c.id=%s AND pl.active=TRUE AND pli.active=TRUE
                     AND (pl.valid_to IS NULL OR pl.valid_to>CURRENT_TIMESTAMP)
                     AND (pli.valid_to IS NULL OR pli.valid_to>CURRENT_TIMESTAMP)
                     AND pli.valid_from<=CURRENT_TIMESTAMP
                     AND pli.product_id=ANY(%s::uuid[])
                     AND pli.min_quantity<=1
                   ORDER BY pli.product_id, pli.min_quantity DESC, pli.valid_from DESC""",
                (customer_id, unresolved),
            )
            price_rows = {str(r[0]): Decimal(str(r[1])) for r in cur.fetchall()}

        remaining = [pid for pid in unresolved if str(pid) not in price_rows]
        master_rows = {}
        if remaining:
            cur.execute(
                """SELECT product_id, final_price
                   FROM price_master
                   WHERE product_id=ANY(%s::uuid[]) AND status='ACTIVE'
                     AND effective_from<=CURRENT_TIMESTAMP
                     AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP)
                   ORDER BY product_id, effective_from DESC""",
                (remaining,),
            )
            master_rows = {str(r[0]): Decimal(str(r[1] or 0)) for r in cur.fetchall()}

        product_rows = {}
        remaining = [pid for pid in unresolved if str(pid) not in price_rows and str(pid) not in master_rows]
        if remaining:
            cur.execute(
                "SELECT id, sale_price, is_active FROM products WHERE id=ANY(%s::uuid[])",
                (remaining,),
            )
            product_rows = {str(r[0]): r for r in cur.fetchall()}

    resolved: list[ItemIn] = []
    for item in items:
        if item.unit_price is not None and item.unit_price > 0:
            resolved.append(item)
            continue
        key = str(item.product_id)
        price = price_rows.get(key) or master_rows.get(key)
        if price is None:
            row = product_rows.get(key)
            if not row or not row[2]:
                raise HTTPException(status_code=422, detail=f"active product not found: {item.product_id}")
            price = Decimal(str(row[1] or 0))
        if price <= 0:
            raise HTTPException(status_code=422, detail=f"product has no valid sale price: {item.product_id}")
        resolved.append(item.model_copy(update={"unit_price": price}))
    return resolved


@router.post("", status_code=201)
def create_order(payload: OrderIn, request: Request, idempotency_key: str | None = Header(default=None)) -> dict[str, Any]:
    if order_center is None:
        raise HTTPException(status_code=503, detail="Order Center is not configured")
    customer_id = payload.customer_id
    if payload.channel.value in {"WEBSITE", "B2B"}:
        session = require_customer_session(request)
        if session["customerId"] != customer_id:
            raise HTTPException(status_code=403, detail="Customer session does not match order customer")
        customer_id = session["customerId"]
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
        ))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{order_no}")
def get_order(order_no: str) -> dict[str, Any]:
    if order_center is None:
        raise HTTPException(status_code=503, detail="Order Center is not configured")
    result = order_center.orders.get(order_no)
    if result is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return result


@router.post("/{order_no}/confirm")
def confirm_order(order_no: str) -> dict[str, Any]:
    if order_center is None:
        raise HTTPException(status_code=503, detail="Order Center is not configured")
    try:
        return order_center.confirm(order_no)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Order not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
