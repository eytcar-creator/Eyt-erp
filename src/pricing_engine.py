"""E.Y.T pricing engine.

Single source of truth for channel pricing. Values are in the same currency
unit supplied by the caller (for example, IRR or toman); the engine does not
perform currency conversion.
"""
from dataclasses import dataclass
from typing import Dict


CHANNEL_FACTORS = {
    "consumer": 1.00,
    "dealer": 0.85,
    "distributor": 0.78,
    "representative": 0.72,
    "provincial_representative_volume": 0.68,
}


@dataclass(frozen=True)
class PricingResult:
    actual_cost: float
    coefficient: float
    mrp: float
    floor_price: float
    channel_prices: Dict[str, float]


def calculate_pricing(
    actual_cost: float,
    coefficient: float,
    minimum_margin: float = 0.15,
) -> PricingResult:
    """Calculate MRP and protected channel prices.

    coefficient is expressed as a multiplier, e.g. 1.40 for 140% of cost.
    minimum_margin is expressed as a decimal, e.g. 0.15 for 15% minimum margin.

    A channel price is never allowed below floor_price. The caller should
    require central approval if a requested commercial price is below it.
    """
    if actual_cost < 0:
        raise ValueError("actual_cost cannot be negative")
    if coefficient <= 0:
        raise ValueError("coefficient must be greater than zero")
    if minimum_margin < 0:
        raise ValueError("minimum_margin cannot be negative")

    mrp = actual_cost * coefficient
    floor_price = actual_cost * (1 + minimum_margin)
    channel_prices = {
        channel: max(mrp * factor, floor_price)
        for channel, factor in CHANNEL_FACTORS.items()
    }
    return PricingResult(
        actual_cost=actual_cost,
        coefficient=coefficient,
        mrp=mrp,
        floor_price=floor_price,
        channel_prices=channel_prices,
    )


def channel_margin(actual_cost: float, selling_price: float) -> float:
    """Return gross margin as a fraction of selling price."""
    if selling_price <= 0:
        raise ValueError("selling_price must be greater than zero")
    return (selling_price - actual_cost) / selling_price
