from decimal import Decimal

import pytest

from api.production.qc_api import BatchInput, InspectionInput, ReleaseInput, TraceInput


def test_batch_requires_positive_plan():
    with pytest.raises(ValueError):
        BatchInput(batch_no="B-1", production_order_no="MO-1", product_code="P-1", planned_qty=Decimal("0"))


def test_inspection_defaults_are_safe():
    payload = InspectionInput(inspection_type="FINAL", result="PASS", inspector="qc")
    assert payload.accepted_qty == Decimal("0")
    assert payload.rejected_qty == Decimal("0")


def test_release_requires_positive_quantity_and_warehouse():
    with pytest.raises(ValueError):
        ReleaseInput(warehouse_code="FG", quantity=Decimal("0"), released_by="qc")


def test_trace_requires_actor():
    with pytest.raises(ValueError):
        TraceInput(event_type="SHIPMENT", actor="")
