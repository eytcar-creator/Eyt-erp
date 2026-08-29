"""Minimal executable production service for E.Y.T ERP.

This module is framework-agnostic. It validates production quantities and
calculates the true production cost, including capital holding cost.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List


@dataclass
class OperationResult:
    operation_code: str
    input_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal = Decimal("0")
    waste_qty: Decimal = Decimal("0")
    service_cost: Decimal = Decimal("0")
    transport_cost: Decimal = Decimal("0")

    def validate(self) -> None:
        total = self.accepted_qty + self.rejected_qty + self.waste_qty
        if self.input_qty < 0 or total < 0:
            raise ValueError("Production quantities cannot be negative")
        if total != self.input_qty:
            raise ValueError(
                "Quantity reconciliation failed: accepted + rejected + waste "
                "must equal input quantity"
            )


@dataclass
class ProductionOrder:
    order_no: str
    product_code: str
    product_name: str
    target_qty: Decimal
    order_date: date
    operations: List[OperationResult] = field(default_factory=list)
    material_cost: Decimal = Decimal("0")
    labor_cost: Decimal = Decimal("0")
    overhead_cost: Decimal = Decimal("0")
    qc_cost: Decimal = Decimal("0")
    scrap_cost: Decimal = Decimal("0")
    customer_prepayment: Decimal = Decimal("0")

    def add_operation(self, operation: OperationResult) -> None:
        operation.validate()
        self.operations.append(operation)

    @property
    def subcontracting_cost(self) -> Decimal:
        return sum((o.service_cost for o in self.operations), Decimal("0"))

    @property
    def transport_cost(self) -> Decimal:
        return sum((o.transport_cost for o in self.operations), Decimal("0"))

    def capital_holding_cost(
        self, holding_days: Decimal, annual_rate: Decimal
    ) -> Decimal:
        base = (
            self.material_cost
            + self.subcontracting_cost
            + self.labor_cost
            + self.transport_cost
            + self.overhead_cost
            + self.qc_cost
            + self.scrap_cost
            - self.customer_prepayment
        )
        if base < 0:
            base = Decimal("0")
        return (base * annual_rate * holding_days / Decimal("365")).quantize(
            Decimal("0.01")
        )

    def true_cost(self, holding_days: Decimal, annual_rate: Decimal) -> Decimal:
        holding = self.capital_holding_cost(holding_days, annual_rate)
        return (
            self.material_cost
            + self.subcontracting_cost
            + self.labor_cost
            + self.transport_cost
            + self.overhead_cost
            + self.qc_cost
            + self.scrap_cost
            + holding
        )


if __name__ == "__main__":
    order = ProductionOrder(
        order_no="MO-ARIO-0001",
        product_code="ARY-TRE-BODY",
        product_name="تنه سیبک فرمان آریو",
        target_qty=Decimal("2000"),
        order_date=date.today(),
    )
    print(order.order_no, order.target_qty)
