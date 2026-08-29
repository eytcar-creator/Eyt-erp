from decimal import Decimal

import pytest

from api.production.operation_api import OperationCompletionInput, validate_quantities


def test_operation_quantities_reconcile():
    payload = OperationCompletionInput(
        sequenceNo=10,
        operationCode="CNC",
        operationName="CNC machining",
        inputQty=Decimal("2000"),
        acceptedQty=Decimal("1980"),
        rejectedQty=Decimal("15"),
        wasteQty=Decimal("5"),
    )
    validate_quantities(payload)


def test_operation_quantities_reject_mismatch():
    payload = OperationCompletionInput(
        sequenceNo=10,
        operationCode="CNC",
        operationName="CNC machining",
        inputQty=Decimal("2000"),
        acceptedQty=Decimal("1980"),
        rejectedQty=Decimal("10"),
        wasteQty=Decimal("5"),
    )
    with pytest.raises(Exception):
        validate_quantities(payload)


def test_operation_quantities_reject_negative():
    payload = OperationCompletionInput(
        sequenceNo=10,
        operationCode="CNC",
        operationName="CNC machining",
        inputQty=Decimal("100"),
        acceptedQty=Decimal("101"),
        rejectedQty=Decimal("-1"),
        wasteQty=Decimal("0"),
    )
    with pytest.raises(Exception):
        validate_quantities(payload)
