from decimal import Decimal

import pytest

from api.production.profit_engine import calculate_profit_quote


def test_sequential_discounts_and_profit_guard() -> None:
    quote = calculate_profit_quote(
        quantity=Decimal("10"),
        list_unit_price=Decimal("1000"),
        unit_cost=Decimal("600"),
        discounts_pct=[Decimal("10"), Decimal("5")],
        rebate_pct=Decimal("2"),
        unit_variable_cost=Decimal("20"),
        shipping_cost=Decimal("100"),
        receivable_days=30,
        annual_finance_rate_pct=Decimal("24"),
        minimum_margin_pct=Decimal("20"),
    )

    assert quote.net_unit_price == Decimal("855.00")
    assert quote.net_sales == Decimal("8379.00")
    assert quote.profit > Decimal("0")
    assert quote.margin_pct > Decimal("20")
    assert quote.status == "GREEN"
    assert quote.maximum_additional_discount_pct > Decimal("0")


def test_red_when_margin_is_below_floor() -> None:
    quote = calculate_profit_quote(
        quantity=Decimal("1"),
        list_unit_price=Decimal("100"),
        unit_cost=Decimal("90"),
        discounts_pct=[Decimal("5")],
        minimum_margin_pct=Decimal("20"),
    )

    assert quote.status == "RED"
    assert quote.profit == Decimal("5.00")
    assert quote.margin_pct < Decimal("20")
    assert quote.maximum_additional_discount_pct == Decimal("0")


def test_invalid_discount_is_rejected() -> None:
    with pytest.raises(ValueError, match="each discount"):
        calculate_profit_quote(
            quantity=Decimal("1"),
            list_unit_price=Decimal("100"),
            unit_cost=Decimal("50"),
            discounts_pct=[Decimal("100")],
            minimum_margin_pct=Decimal("10"),
        )
