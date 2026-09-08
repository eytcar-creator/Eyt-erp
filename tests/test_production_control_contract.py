from decimal import Decimal
import pytest
from fastapi import HTTPException
from api.production.operation_api import OperationCompletionInput, validate_quantities
from api.production.production_control_api import OrderInput

def test_operation_quantities_must_balance():
    payload=OperationCompletionInput(sequenceNo=20,operationCode="OP-020",operationName="فورج",inputQty=Decimal("100"),acceptedQty=Decimal("90"),rejectedQty=Decimal("5"),wasteQty=Decimal("5"))
    validate_quantities(payload)

def test_operation_quantities_reject_mismatch():
    payload=OperationCompletionInput(sequenceNo=20,operationCode="OP-020",operationName="فورج",inputQty=Decimal("100"),acceptedQty=Decimal("91"),rejectedQty=Decimal("5"),wasteQty=Decimal("5"))
    with pytest.raises(HTTPException) as exc: validate_quantities(payload)
    assert exc.value.status_code==409

def test_order_requires_positive_target():
    with pytest.raises(ValueError): OrderInput(order_no="PO-1",product_code="EYT-1",product_name="test",target_qty=0,order_date="2026-09-08")
