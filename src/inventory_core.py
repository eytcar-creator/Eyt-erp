"""E.Y.T Inventory core v1."""

from dataclasses import dataclass
from decimal import Decimal

@dataclass
class StockItem:
    sku: str
    warehouse: str
    on_hand: Decimal = Decimal("0")
    reserved: Decimal = Decimal("0")
    reorder_point: Decimal = Decimal("0")

    @property
    def available(self):
        return self.on_hand - self.reserved

    @property
    def needs_reorder(self):
        return self.available <= self.reorder_point

    def reserve(self, quantity):
        quantity = Decimal(str(quantity))
        if quantity > self.available:
            raise ValueError("Insufficient available stock")
        self.reserved += quantity

    def release(self, quantity):
        self.reserved -= Decimal(str(quantity))
