from decimal import Decimal
from api.pricing.engine import CostInput, PricingPolicy, calculate_daily_price

def test_daily_price_allocates_setup_and_scrap():
    result = calculate_daily_price(
        CostInput(
            material=Decimal("100000"),
            direct_labor=Decimal("20000"),
            machine=Decimal("5000"),
            setup_total=Decimal("30000"),
            setup_batch_qty=Decimal("1000"),
            packaging=Decimal("2000"),
            qc=Decimal("1000"),
            overhead=Decimal("7000"),
            scrap_rate=Decimal("0.05"),
            accepted_qty=Decimal("950"),
        ),
        PricingPolicy(
            target_margin=Decimal("0.20"),
            channel_discounts={"dealer": Decimal("0.10"), "wholesale": Decimal("0.05")},
        ),
    )
    assert result["setup_per_unit"] == Decimal("30.00")
    assert result["direct_cost"] == Decimal("135030.00")
    assert result["true_unit_cost"] == Decimal("142136.84")
    assert result["base_selling_price"] == Decimal("177671.05")
    assert result["channel_prices"]["dealer"] == Decimal("159903.95")

def test_margin_is_on_selling_price_not_cost_plus_margin():
    result = calculate_daily_price(
        CostInput(material=Decimal("800")),
        PricingPolicy(target_margin=Decimal("0.20")),
    )
    assert result["base_selling_price"] == Decimal("1000.00")
