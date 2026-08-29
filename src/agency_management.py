"""E.Y.T Agency Management v1."""

from dataclasses import dataclass
from decimal import Decimal

@dataclass
class Agency:
    code: str
    city: str
    province: str
    status: str = "trial"
    exclusivity: bool = False
    monthly_target: Decimal = Decimal("0")
    score: Decimal = Decimal("0")

    def evaluate(self, sales_ratio, collection_ratio, market_coverage_ratio):
        self.score = (
            Decimal(str(sales_ratio)) * Decimal("0.50")
            + Decimal(str(collection_ratio)) * Decimal("0.30")
            + Decimal(str(market_coverage_ratio)) * Decimal("0.20")
        ) * Decimal("100")
        return self.score

    def qualifies_for_exclusivity(self):
        return self.score >= Decimal("85")
