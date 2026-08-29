from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .auth import require_permission

router = APIRouter(prefix="/api/procurement", tags=["procurement"])


class PurchaseLine(BaseModel):
    sku: str
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class PurchaseRequest(BaseModel):
    supplier_id: str
    lines: list[PurchaseLine] = Field(min_length=1)


@router.post("/estimate")
def estimate(payload: PurchaseRequest, _=Depends(require_permission("procurement.read"))):
    total = sum((x.quantity * x.unit_price for x in payload.lines), Decimal("0"))
    return {
        "supplier_id": payload.supplier_id,
        "line_count": len(payload.lines),
        "total": total,
        "currency": "IRR",
    }
