"""E.Y.T Production Order v1."""

from dataclasses import dataclass
from decimal import Decimal

@dataclass
class ProductionOrder:
    number: str
    sku: str
    planned_quantity: Decimal
    produced_quantity: Decimal = Decimal("0")
    scrap_quantity: Decimal = Decimal("0")
    status: str = "planned"

    def start(self):
        self.status = "in_progress"
        return self

    def complete(self, produced_quantity, scrap_quantity=0):
        self.produced_quantity = Decimal(str(produced_quantity))
        self.scrap_quantity = Decimal(str(scrap_quantity))
        if self.produced_quantity + self.scrap_quantity > self.planned_quantity:
            raise ValueError("Production quantity exceeds plan")
        self.status = "completed"
        return self
