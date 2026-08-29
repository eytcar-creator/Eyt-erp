"""E.Y.T Product Master and BOM v1."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from costing_engine import CostSheet

@dataclass
class BOMItem:
    component_sku: str
    component_name: str
    unit_cost: Decimal
    quantity: Decimal

    @property
    def line_cost(self):
        return self.unit_cost * self.quantity

@dataclass
class Product:
    sku: str
    name: str
    family: str
    vehicle: Optional[str] = None
    active: bool = True
    pricing_coefficient: Decimal = Decimal("1.40")
    bom: List[BOMItem] = field(default_factory=list)

    def to_cost_sheet(self, workshop=0, packaging=0, freight=0, scrap=0, capital_sleep=0, other=0):
        materials = {item.component_name: item.line_cost for item in self.bom}
        return CostSheet(
            sku=self.sku, product_name=self.name,
            direct_materials=materials, workshop=Decimal(str(workshop)),
            packaging=Decimal(str(packaging)), freight=Decimal(str(freight)),
            scrap=Decimal(str(scrap)), capital_sleep=Decimal(str(capital_sleep)),
            other=Decimal(str(other)),
        )
