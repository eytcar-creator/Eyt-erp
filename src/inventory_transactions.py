"""E.Y.T Inventory Transactions v1."""

from dataclasses import dataclass
from decimal import Decimal
from inventory_core import StockItem

@dataclass
class InventoryTransaction:
    sku: str
    warehouse: str
    transaction_type: str
    quantity: Decimal

def apply_transaction(stock: StockItem, transaction: InventoryTransaction):
    qty = Decimal(str(transaction.quantity))
    if transaction.transaction_type in ("production_receipt", "purchase_receipt", "transfer_in", "return_in"):
        stock.on_hand += qty
    elif transaction.transaction_type in ("sales_issue", "transfer_out", "scrap"):
        if qty > stock.available:
            raise ValueError("Insufficient available stock")
        stock.on_hand -= qty
    else:
        raise ValueError("Unknown inventory transaction type")
    return stock
