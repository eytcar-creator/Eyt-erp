from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .auth import require_permission

router = APIRouter(prefix="/api/sales", tags=["sales"])


class SalesLine(BaseModel):
    sku: str
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    unit_cost: Decimal = Field(ge=0)


class SalesOrder(BaseModel):
    customer_id: str
    lines: list[SalesLine] = Field(min_length=1)
    prepayment: Decimal = Field(default=Decimal("0"), ge=0)


@router.post("/quote")
def quote(payload: SalesOrder, _=Depends(require_permission("sales.write"))):
    subtotal = sum((x.quantity * x.unit_price for x in payload.lines), Decimal("0"))
    cost = sum((x.quantity * x.unit_cost for x in payload.lines), Decimal("0"))
    gross_profit = subtotal - cost
    balance = max(Decimal("0"), subtotal - payload.prepayment)
    margin = (gross_profit / subtotal * Decimal("100")) if subtotal else Decimal("0")
    return {
        "customer_id": payload.customer_id,
        "subtotal": subtotal,
        "prepayment": payload.prepayment,
        "balance_due": balance,
        "cost": cost,
        "gross_profit": gross_profit,
        "margin_percent": margin.quantize(Decimal("0.01")),
    }
