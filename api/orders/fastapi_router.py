from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import psycopg
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .order_center import CreateOrder, OrderChannel, OrderCenter, OrderLine

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


def _resolve_prices(items: list[ItemIn]) -> list[ItemIn]:
    """Resolve omitted/zero prices from canonical Master Data."""
    unresolved = [i.product_id for i in items if i.unit_price is None or i.unit_price <= 0]
    if not unresolved:
        return items
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, sale_price, is_active FROM products WHERE id = ANY(%s::uuid[])",
            (unresolved,),
        )
        rows = {str(row[0]): row for row in cur.fetchall()}
    resolved: list[ItemIn] = []
    for item in items:
        if item.unit_price is not None and item.unit_price > 0:
            resolved.append(item)
            continue
        row = rows.get(str(item.product_id))
        if not row or not row[2]:
            raise HTTPException(status_code=422, detail=f"active product not found: {item.product_id}")
        price = Decimal(str(row[1] or 0))
        if price <= 0:
            raise HTTPException(status_code=422, detail=f"product has no valid sale price: {item.product_id}")
        resolved.append(item.model_copy(update={"unit_price": price}))
    return resolved


@router.post("", status_code=201)
def create_order(payload: OrderIn, idempotency_key: str | None = Header(default=None)) -> dict[str, Any]:
    if order_center is None:
        raise HTTPException(status_code=503, detail="Order Center is not configured")
    try:
        priced_items = _resolve_prices(payload.items)
        lines = tuple(
            OrderLine(product_id=i.product_id, quantity=i.quantity, unit_price=i.unit_price or Decimal("0"))
            for i in priced_items
        )
        if any(line.unit_price <= 0 for line in lines):
            raise ValueError("every order line must have a positive unit price")
        return order_center.create(CreateOrder(
            customer_id=payload.customer_id,
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
