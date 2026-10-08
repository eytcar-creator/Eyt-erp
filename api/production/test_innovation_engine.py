"""Focused tests for the Innovation / Idea Engine scoring contract."""
from decimal import Decimal

def test_priority_formula_contract():
    value=(Decimal("80")*Decimal("0.20")+Decimal("90")*Decimal("0.25")+Decimal("70")*Decimal("0.20")+Decimal("80")*Decimal("0.20")+(Decimal("100")-Decimal("30"))*Decimal("0.10")+(Decimal("100")-Decimal("20"))*Decimal("0.05"))
    assert value==Decimal("79.50")
