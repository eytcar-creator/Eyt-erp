from datetime import date
from decimal import Decimal

import pytest

from api.production.production_service import OperationResult, ProductionOrder


def make_order() -> ProductionOrder:
    return ProductionOrder(
        order_no="MO-ARIO-0001",
        product_code="ARY-TRE-BODY",
        product_name="تنه سیبک فرمان آریو",
        target_qty=Decimal("2000"),
        order_date=date.today(),
        material_cost=Decimal("100000000"),
        labor_cost=Decimal("10000000"),
        overhead_cost=Decimal("5000000"),
        qc_cost=Decimal("1000000"),
        scrap_cost=Decimal("2000000"),
        customer_prepayment=Decimal("20000000"),
    )


def test_operation_quantity_reconciliation():
    op = OperationResult(
        "FORGE", Decimal("2000"), Decimal("1970"), Decimal("20"), Decimal("10")
    )
    op.validate()


def test_invalid_operation_quantities_are_rejected():
    op = OperationResult(
        "CNC", Decimal("2000"), Decimal("1970"), Decimal("20"), Decimal("20")
    )
    with pytest.raises(ValueError):
        op.validate()


def test_prepayment_reduces_holding_cost_base():
    order = make_order()
    order.add_operation(
        OperationResult(
            "FORGE",
            Decimal("2000"),
            Decimal("2000"),
            service_cost=Decimal("10000000"),
            transport_cost=Decimal("1000000"),
        )
    )
    cost = order.capital_holding_cost(Decimal("30"), Decimal("0.30"))
    assert cost == Decimal("3698630.14")
