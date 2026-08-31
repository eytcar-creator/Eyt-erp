from __future__ import annotations

from decimal import Decimal
from typing import Any

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


# Application startup should inject the real PostgreSQL-backed service here.
order_center: OrderCenter | None = None


def configure_order_center(service: OrderCenter) -> None:
    global order_center
    order_center = service


@router.post("", status_code=201)
def create_order(payload: OrderIn, idempotency_key: str | None = Header(default=None)) -> dict[str, Any]:
    if order_center is None:
        raise HTTPException(status_code=503, detail="Order Center is not configured")
    try:
        lines = tuple(
            OrderLine(product_id=i.product_id, quantity=i.quantity, unit_price=i.unit_price or Decimal("0"))
            for i in payload.items
        )
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
