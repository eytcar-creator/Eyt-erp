from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .auth import require_permission
from .finance_api import calculate_cash_cycle_days, calculate_receivable

router = APIRouter(prefix="/api/finance", tags=["finance"])


class ReceivableInput(BaseModel):
    invoice_total: Decimal = Field(ge=0)
    collected: Decimal = Field(ge=0)


class CashCycleInput(BaseModel):
    material_date: date
    sale_date: date
    collection_date: date


@router.post("/receivable")
def receivable(payload: ReceivableInput, _=Depends(require_permission("finance.read"))):
    return {"receivable": calculate_receivable(payload.invoice_total, payload.collected)}


@router.post("/cash-cycle")
def cash_cycle(payload: CashCycleInput, _=Depends(require_permission("finance.read"))):
    return {
        "material_to_sale_days": (payload.sale_date - payload.material_date).days,
        "sale_to_collection_days": (payload.collection_date - payload.sale_date).days,
        "cash_cycle_days": calculate_cash_cycle_days(
            payload.material_date, payload.sale_date, payload.collection_date
        ),
    }
