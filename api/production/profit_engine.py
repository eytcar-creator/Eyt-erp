from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0")
HUNDRED = Decimal("100")
DAYS_PER_YEAR = Decimal("365")


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def pct(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ProfitQuote:
    quantity: Decimal
    list_unit_price: Decimal
    net_unit_price: Decimal
    unit_cost: Decimal
    unit_variable_cost: Decimal
    shipping_cost: Decimal
    financing_cost: Decimal
    rebate_amount: Decimal
    net_sales: Decimal
    total_cost: Decimal
    profit: Decimal
    margin_pct: Decimal
    minimum_margin_pct: Decimal
    maximum_additional_discount_pct: Decimal
    status: str


def calculate_profit_quote(
    *,
    quantity: Decimal,
    list_unit_price: Decimal,
    unit_cost: Decimal,
    discounts_pct: list[Decimal] | None = None,
    rebate_pct: Decimal = ZERO,
    unit_variable_cost: Decimal = ZERO,
    shipping_cost: Decimal = ZERO,
    receivable_days: int = 0,
    annual_finance_rate_pct: Decimal = ZERO,
    minimum_margin_pct: Decimal,
    warning_margin_pct: Decimal | None = None,
) -> ProfitQuote:
    """Calculate an order-level profit guard without replacing existing costing.

    Discounts are applied sequentially. Cost inputs are supplied by the existing
    costing/inventory layers; this function only evaluates the commercial decision.
    """
    if quantity <= ZERO:
        raise ValueError("quantity must be positive")
    if list_unit_price < ZERO or unit_cost < ZERO or unit_variable_cost < ZERO:
        raise ValueError("prices and costs cannot be negative")
    if shipping_cost < ZERO or rebate_pct < ZERO or minimum_margin_pct < ZERO:
        raise ValueError("costs, rebate and minimum margin cannot be negative")
    if receivable_days < 0 or annual_finance_rate_pct < ZERO:
        raise ValueError("receivable days and finance rate cannot be negative")
    if minimum_margin_pct >= HUNDRED:
        raise ValueError("minimum margin must be below 100%")

    discounts = discounts_pct or []
    net_unit_price = list_unit_price
    for discount in discounts:
        if discount < ZERO or discount >= HUNDRED:
            raise ValueError("each discount must be in [0, 100)")
        net_unit_price *= (HUNDRED - discount) / HUNDRED

    net_unit_price = money(net_unit_price)
    net_sales_before_rebate = money(quantity * net_unit_price)
    rebate_amount = money(net_sales_before_rebate * rebate_pct / HUNDRED)
    net_sales = money(net_sales_before_rebate - rebate_amount)

    financing_cost = money(
        net_sales
        * annual_finance_rate_pct
        / HUNDRED
        * Decimal(receivable_days)
        / DAYS_PER_YEAR
    )
    direct_cost = money(quantity * (unit_cost + unit_variable_cost))
    total_cost = money(direct_cost + shipping_cost + financing_cost)
    profit = money(net_sales - total_cost)
    margin_pct = pct((profit / net_sales) * HUNDRED) if net_sales > ZERO else ZERO

    warning = warning_margin_pct if warning_margin_pct is not None else minimum_margin_pct
    if margin_pct >= minimum_margin_pct:
        status = "GREEN"
    elif margin_pct >= warning:
        status = "YELLOW"
    else:
        status = "RED"

    # Maximum extra discount while preserving the minimum margin.
    fixed_cost_per_unit = (total_cost / quantity) if quantity else ZERO
    required_net_unit = fixed_cost_per_unit / (HUNDRED - minimum_margin_pct) * HUNDRED
    if net_unit_price <= ZERO or required_net_unit >= net_unit_price:
        maximum_additional_discount_pct = ZERO
    else:
        maximum_additional_discount_pct = pct(
            (HUNDRED - (required_net_unit / net_unit_price * HUNDRED))
        )

    return ProfitQuote(
        quantity=quantity,
        list_unit_price=list_unit_price,
        net_unit_price=net_unit_price,
        unit_cost=unit_cost,
        unit_variable_cost=unit_variable_cost,
        shipping_cost=shipping_cost,
        financing_cost=financing_cost,
        rebate_amount=rebate_amount,
        net_sales=net_sales,
        total_cost=total_cost,
        profit=profit,
        margin_pct=margin_pct,
        minimum_margin_pct=minimum_margin_pct,
        maximum_additional_discount_pct=maximum_additional_discount_pct,
        status=status,
    )
