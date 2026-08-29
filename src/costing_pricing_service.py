"""Integration layer between E.Y.T costing and pricing.

The costing engine provides actual_cost. Pricing policy converts it to
MRP and channel prices while enforcing the E.Y.T floor price.
"""

from decimal import Decimal
from costing_engine import CostSheet

CHANNELS = {
    "consumer": Decimal("1.00"),
    "dealer": Decimal("0.85"),
    "distributor": Decimal("0.78"),
    "representative": Decimal("0.72"),
    "provincial_representative_volume": Decimal("0.68"),
}

def calculate_price_book(cost_sheet: CostSheet, pricing_coefficient, minimum_margin=Decimal("0.15")):
    actual_cost = cost_sheet.actual_cost()
    coefficient = Decimal(str(pricing_coefficient))
    minimum_margin = Decimal(str(minimum_margin))

    mrp = actual_cost * coefficient
    floor_price = actual_cost * (Decimal("1") + minimum_margin)

    prices = {}
    for channel, ratio in CHANNELS.items():
        calculated = mrp * ratio
        prices[channel] = max(calculated, floor_price)

    return {
        "sku": cost_sheet.sku,
        "product_name": cost_sheet.product_name,
        "actual_cost": actual_cost,
        "pricing_coefficient": coefficient,
        "mrp": mrp,
        "floor_price": floor_price,
        "channels": prices,
    }
