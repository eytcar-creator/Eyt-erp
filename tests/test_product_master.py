from decimal import Decimal

from api.production.product_master_api import FitmentInput, ProductInput


def test_product_master_input_defaults_are_operational():
    item = ProductInput(sku="EYT-SBK-001", productCode="EYT-SBK-001", nameFa="سیبک فرمان")
    assert item.brand == "E.Y.T"
    assert item.unit == "PCS"
    assert item.productType == "FINISHED_GOOD"
    assert item.reorderPoint == Decimal("0")


def test_fitment_rejects_invalid_year_range_at_api_boundary():
    fitment = FitmentInput(make="MVM", model="315", yearFrom=2020, yearTo=2024)
    assert fitment.yearTo >= fitment.yearFrom
