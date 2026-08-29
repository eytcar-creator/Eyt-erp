from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .auth import require_permission
from .costing import true_cost, unit_cost

router = APIRouter(prefix="/api/costing", tags=["costing"])


class CostInput(BaseModel):
    material: Decimal = Field(default=Decimal("0"), ge=0)
    subcontracting: Decimal = Field(default=Decimal("0"), ge=0)
    labor: Decimal = Field(default=Decimal("0"), ge=0)
    transport: Decimal = Field(default=Decimal("0"), ge=0)
    overhead: Decimal = Field(default=Decimal("0"), ge=0)
    qc: Decimal = Field(default=Decimal("0"), ge=0)
    scrap: Decimal = Field(default=Decimal("0"), ge=0)
    holdingDays: Decimal = Field(default=Decimal("0"), ge=0)
    annualRate: Decimal = Field(default=Decimal("0"), ge=0)
    customerPrepayment: Decimal = Field(default=Decimal("0"), ge=0)
    acceptedQty: Decimal = Field(default=Decimal("0"), ge=0)


@router.post("/calculate")
def calculate_cost(payload: CostInput, _=Depends(require_permission("production.read"))):
    result = true_cost(
        payload.material, payload.subcontracting, payload.labor,
        payload.transport, payload.overhead, payload.qc, payload.scrap,
        payload.holdingDays, payload.annualRate, payload.customerPrepayment,
    )
    result["unit_cost"] = unit_cost(result["true_cost"], payload.acceptedQty) if payload.acceptedQty > 0 else Decimal("0")
    return result
