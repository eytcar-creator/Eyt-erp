from decimal import Decimal

from api.production.costing import true_cost, unit_cost


def test_true_cost_includes_holding_and_prepayment():
    result = true_cost(
        material=Decimal("100000000"),
        subcontracting=Decimal("25000000"),
        labor=Decimal("10000000"),
        transport=Decimal("5000000"),
        overhead=Decimal("5000000"),
        qc=Decimal("1000000"),
        scrap=Decimal("2000000"),
        holding_days=Decimal("30"),
        annual_rate=Decimal("0.30"),
        customer_prepayment=Decimal("20000000"),
    )
    assert result["capital_base"] == Decimal("128000000")
    assert result["holding_cost"] == Decimal("3156164.38")
    assert result["true_cost"] == Decimal("16156164.38") + Decimal("128000000") + Decimal("20000000")


def test_unit_cost_requires_accepted_quantity():
    try:
        unit_cost(Decimal("100"), Decimal("0"))
    except ValueError:
        return
    raise AssertionError("Expected ValueError")
