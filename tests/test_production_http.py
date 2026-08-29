from decimal import Decimal

import pytest

from api.production.production_http import complete_operation, create_order, repository


def test_create_and_complete_ario_order():
    repository.orders.clear()
    result = create_order({
        "orderNo": "MO-ARIO-0001",
        "productCode": "ARY-TRE-BODY",
        "productName": "تنه سیبک فرمان آریو",
        "targetQty": 2000,
        "orderDate": "2026-08-26",
    })
    assert result["status"] == "planned"

    result = complete_operation(
        "MO-ARIO-0001",
        "FORGE",
        {
            "inputQty": 2000,
            "acceptedQty": 1970,
            "rejectedQty": 20,
            "wasteQty": 10,
            "serviceCost": 15000000,
            "transportCost": 1000000,
        },
    )
    assert result["status"] == "completed"
    assert Decimal(str(result["operation"]["accepted_qty"])) == Decimal("1970")


def test_unknown_order_fails():
    with pytest.raises(KeyError):
        complete_operation("UNKNOWN", "CNC", {
            "inputQty": 10,
            "acceptedQty": 10,
            "rejectedQty": 0,
            "wasteQty": 0,
        })
