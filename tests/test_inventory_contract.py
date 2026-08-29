from decimal import Decimal

import pytest

from api.production.inventory_api import ALL_TYPES, NEGATIVE_TYPES, POSITIVE_TYPES, BomInput, TransactionInput


def test_inventory_transaction_type_contract_is_complete():
    assert POSITIVE_TYPES | NEGATIVE_TYPES == {
        "RECEIPT", "ISSUE", "TRANSFER_OUT", "TRANSFER_IN", "CONSUMPTION",
        "RETURN", "SCRAP", "PRODUCTION_RECEIPT", "ADJUSTMENT",
    }
    assert ALL_TYPES == POSITIVE_TYPES | NEGATIVE_TYPES


def test_transaction_input_rejects_non_positive_quantity():
    with pytest.raises(Exception):
        TransactionInput(productCode="P-1", warehouseCode="MAIN", quantity=Decimal("0"), transactionType="RECEIPT")


def test_bom_defaults_to_draft_without_shared_mutable_items():
    first = BomInput(bomCode="BOM-1", productCode="P-1", version="1")
    second = BomInput(bomCode="BOM-2", productCode="P-2", version="1")
    assert first.status == "DRAFT"
    assert first.items == [] and second.items == []
    assert first.items is not second.items
