"""E.Y.T Billing and Collection v1."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

@dataclass
class InvoiceLine:
    sku: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def total(self):
        return self.quantity * self.unit_price

@dataclass
class Invoice:
    number: str
    customer_code: str
    lines: List[InvoiceLine] = field(default_factory=list)
    status: str = "issued"
    paid_amount: Decimal = Decimal("0")

    @property
    def total(self):
        return sum((line.total for line in self.lines), Decimal("0"))

    @property
    def balance(self):
        return self.total - self.paid_amount

    def receive(self, amount):
        amount = Decimal(str(amount))
        if amount <= 0 or self.paid_amount + amount > self.total:
            raise ValueError("Invalid receipt amount")
        self.paid_amount += amount
        if self.balance == 0:
            self.status = "paid"
        elif self.paid_amount > 0:
            self.status = "partially_paid"
        return self
