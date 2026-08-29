"""E.Y.T ERP Costing Engine v1.

Computes unit cost from direct materials and operational cost buckets.
All monetary values are stored in Tomans per unit.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict

MONEY_Q = Decimal("1")

def money(value) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_Q, rounding=ROUND_HALF_UP)

@dataclass
class CostSheet:
    sku: str
    product_name: str
    direct_materials: Dict[str, Decimal] = field(default_factory=dict)
    workshop: Decimal = Decimal("0")
    packaging: Decimal = Decimal("0")
    freight: Decimal = Decimal("0")
    scrap: Decimal = Decimal("0")
    capital_sleep: Decimal = Decimal("0")
    other: Decimal = Decimal("0")

    def material_total(self) -> Decimal:
        return sum((money(v) for v in self.direct_materials.values()), Decimal("0"))

    def actual_cost(self) -> Decimal:
        return money(
            self.material_total()
            + money(self.workshop)
            + money(self.packaging)
            + money(self.freight)
            + money(self.scrap)
            + money(self.capital_sleep)
            + money(self.other)
        )

    def breakdown(self):
        return {
            "materials": self.material_total(),
            "workshop": money(self.workshop),
            "packaging": money(self.packaging),
            "freight": money(self.freight),
            "scrap": money(self.scrap),
            "capital_sleep": money(self.capital_sleep),
            "other": money(self.other),
            "actual_cost": self.actual_cost(),
        }

def haima_s7_qarqari_example() -> CostSheet:
    return CostSheet(
        sku="EYT-HS7-QARQARI-001",
        product_name="قرقری هایما S7",
        direct_materials={
            "میله": Decimal("180000"),
            "کائوچو": Decimal("15000"),
            "گریس": Decimal("5000"),
            "فنجانی": Decimal("75000"),
        },
        packaging=Decimal("24000"),
        workshop=Decimal("100000"),
    )
