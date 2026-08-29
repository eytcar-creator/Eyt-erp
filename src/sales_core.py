"""E.Y.T Sales Order core v1."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

@dataclass
class DealerAccount:
    code: str
    name: str
    credit_limit: Decimal
    outstanding: Decimal = Decimal("0")

    @property
    def available_credit(self):
        return self.credit_limit - self.outstanding

    def approve_amount(self, amount):
        return Decimal(str(amount)) <= self.available_credit

@dataclass
class SalesLine:
    sku: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def total(self):
        return self.quantity * self.unit_price

@dataclass
class SalesOrder:
    number: str
    account: DealerAccount
    lines: List[SalesLine] = field(default_factory=list)
    status: str = "draft"

    @property
    def total(self):
        return sum((line.total for line in self.lines), Decimal("0"))

    def confirm(self):
        if not self.account.approve_amount(self.total):
            raise ValueError("Credit limit exceeded")
        self.account.outstanding += self.total
        self.status = "confirmed"
        return self
