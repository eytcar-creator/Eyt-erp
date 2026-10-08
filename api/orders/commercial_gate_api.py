from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .commercial_gate import CommercialGate, CommercialLine

router = APIRouter(prefix="/api/v1/ai-order-agent", tags=["E.Y.T One - Commercial Gate"])
commercial_gate = CommercialGate()


class CommercialItemIn(BaseModel):
    product_id: str
    quantity: Decimal = Field(gt=0)


class CommercialGateIn(BaseModel):
    customer_id: str
    warehouse_code: str = "MAIN"
    payment_type: str = "CASH"
    items: list[CommercialItemIn] = Field(min_length=1)


@router.post("/commercial-gate")
def evaluate_commercial_gate(payload: CommercialGateIn) -> dict[str, Any]:
    """Evaluate price, stock and credit without mutating ERP state."""
    if payload.payment_type not in {"CASH", "CREDIT"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="payment_type must be CASH or CREDIT")
    try:
        return commercial_gate.evaluate(
            customer_id=payload.customer_id,
            warehouse_code=payload.warehouse_code,
            payment_type=payload.payment_type,
            items=tuple(
                CommercialLine(product_id=i.product_id, quantity=i.quantity)
                for i in payload.items
            ),
        )
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(exc)) from exc
