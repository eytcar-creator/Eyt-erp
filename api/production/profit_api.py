from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .auth import require_permission
from .profit_engine import ProfitQuote, calculate_profit_quote

router = APIRouter(prefix="/api/profit", tags=["profit-first"])


class ProfitQuoteInput(BaseModel):
    quantity: Decimal = Field(gt=0)
    listUnitPrice: Decimal = Field(ge=0)
    unitCost: Decimal = Field(ge=0)
    discountsPct: list[Decimal] = Field(default_factory=list)
    rebatePct: Decimal = Field(default=Decimal("0"), ge=0)
    unitVariableCost: Decimal = Field(default=Decimal("0"), ge=0)
    shippingCost: Decimal = Field(default=Decimal("0"), ge=0)
    receivableDays: int = Field(default=0, ge=0)
    annualFinanceRatePct: Decimal = Field(default=Decimal("0"), ge=0)
    minimumMarginPct: Decimal = Field(ge=0, lt=100)
    warningMarginPct: Decimal | None = Field(default=None, ge=0, lt=100)


def serialize(quote: ProfitQuote) -> dict[str, object]:
    return {
        "quantity": quote.quantity,
        "listUnitPrice": quote.list_unit_price,
        "netUnitPrice": quote.net_unit_price,
        "unitCost": quote.unit_cost,
        "unitVariableCost": quote.unit_variable_cost,
        "shippingCost": quote.shipping_cost,
        "financingCost": quote.financing_cost,
        "rebateAmount": quote.rebate_amount,
        "netSales": quote.net_sales,
        "totalCost": quote.total_cost,
        "profit": quote.profit,
        "marginPct": quote.margin_pct,
        "minimumMarginPct": quote.minimum_margin_pct,
        "maximumAdditionalDiscountPct": quote.maximum_additional_discount_pct,
        "status": quote.status,
    }


@router.post("/quote")
def profit_quote(payload: ProfitQuoteInput, _=Depends(require_permission("sales.read"))):
    quote = calculate_profit_quote(
        quantity=payload.quantity,
        list_unit_price=payload.listUnitPrice,
        unit_cost=payload.unitCost,
        discounts_pct=payload.discountsPct,
        rebate_pct=payload.rebatePct,
        unit_variable_cost=payload.unitVariableCost,
        shipping_cost=payload.shippingCost,
        receivable_days=payload.receivableDays,
        annual_finance_rate_pct=payload.annualFinanceRatePct,
        minimum_margin_pct=payload.minimumMarginPct,
        warning_margin_pct=payload.warningMarginPct,
    )
    return serialize(quote)
