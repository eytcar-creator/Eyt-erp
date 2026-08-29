"""Production costing helpers for E.Y.T ERP."""
from decimal import Decimal


def true_cost(
    material: Decimal,
    subcontracting: Decimal,
    labor: Decimal,
    transport: Decimal,
    overhead: Decimal,
    qc: Decimal,
    scrap: Decimal,
    holding_days: Decimal,
    annual_rate: Decimal,
    customer_prepayment: Decimal = Decimal("0"),
) -> dict[str, Decimal]:
    gross = material + subcontracting + labor + transport + overhead + qc + scrap
    capital_base = max(Decimal("0"), gross - customer_prepayment)
    holding = (capital_base * annual_rate * holding_days / Decimal("365")).quantize(Decimal("0.01"))
    total = gross + holding
    return {
        "gross_cost": gross,
        "capital_base": capital_base,
        "holding_cost": holding,
        "true_cost": total,
    }


def unit_cost(total_cost: Decimal, accepted_qty: Decimal) -> Decimal:
    if accepted_qty <= 0:
        raise ValueError("Accepted quantity must be greater than zero")
    return (total_cost / accepted_qty).quantize(Decimal("0.01"))
