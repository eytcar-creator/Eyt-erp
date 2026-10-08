"""Pure calculation engine for E.Y.T daily product costing and pricing."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict

MONEY = Decimal("0.01")

def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)

@dataclass(frozen=True)
class CostInput:
    material: Decimal = Decimal("0")
    purchased_parts: Decimal = Decimal("0")
    direct_labor: Decimal = Decimal("0")
    machine: Decimal = Decimal("0")
    energy: Decimal = Decimal("0")
    subcontracting: Decimal = Decimal("0")
    tooling: Decimal = Decimal("0")
    setup_total: Decimal = Decimal("0")
    setup_batch_qty: Decimal = Decimal("0")
    packaging: Decimal = Decimal("0")
    qc: Decimal = Decimal("0")
    transport: Decimal = Decimal("0")
    overhead: Decimal = Decimal("0")
    scrap_rate: Decimal = Decimal("0")
    accepted_qty: Decimal = Decimal("1")

@dataclass(frozen=True)
class PricingPolicy:
    target_margin: Decimal = Decimal("0.20")
    channel_discounts: Dict[str, Decimal] | None = None

def calculate_daily_price(cost: CostInput, policy: PricingPolicy) -> dict:
    if cost.accepted_qty <= 0:
        raise ValueError("accepted_qty must be greater than zero")
    if cost.setup_batch_qty < 0:
        raise ValueError("setup_batch_qty cannot be negative")
    if not Decimal("0") <= policy.target_margin < Decimal("1"):
        raise ValueError("target_margin must be between 0 and 1")
    if not Decimal("0") <= cost.scrap_rate < Decimal("1"):
        raise ValueError("scrap_rate must be between 0 and 1")

    setup_per_unit = (
        cost.setup_total / cost.setup_batch_qty
        if cost.setup_batch_qty > 0 else Decimal("0")
    )

    direct_cost = (
        cost.material + cost.purchased_parts + cost.direct_labor
        + cost.machine + cost.energy + cost.subcontracting + cost.tooling
        + setup_per_unit + cost.packaging + cost.qc + cost.transport
        + cost.overhead
    )

    true_unit_cost = direct_cost / (Decimal("1") - cost.scrap_rate)
    selling_price = true_unit_cost / (Decimal("1") - policy.target_margin)

    channels = {}
    for channel, discount in (policy.channel_discounts or {}).items():
        if not Decimal("0") <= discount < Decimal("1"):
            raise ValueError("invalid discount for channel: " + channel)
        channels[channel] = money(selling_price * (Decimal("1") - discount))

    return {
        "direct_cost": money(direct_cost),
        "setup_per_unit": money(setup_per_unit),
        "true_unit_cost": money(true_unit_cost),
        "target_margin": policy.target_margin,
        "base_selling_price": money(selling_price),
        "channel_prices": channels,
    }
