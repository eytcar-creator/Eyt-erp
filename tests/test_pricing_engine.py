import pytest

from src.pricing_engine import calculate_pricing, channel_margin


def test_hyundai_s7_example_uses_floor_price():
    # All figures are in thousand tomans, matching the project example.
    result = calculate_pricing(actual_cost=399, coefficient=1.40, minimum_margin=0.15)

    assert result.mrp == pytest.approx(558.6)
    assert result.floor_price == pytest.approx(458.85)
    assert result.channel_prices["consumer"] == pytest.approx(558.6)
    assert result.channel_prices["dealer"] == pytest.approx(474.81)
    assert result.channel_prices["distributor"] == pytest.approx(458.85)
    assert result.channel_prices["representative"] == pytest.approx(458.85)
    assert result.channel_prices["provincial_representative_volume"] == pytest.approx(458.85)


def test_channel_margin():
    assert channel_margin(399, 500) == pytest.approx(0.202)


def test_invalid_cost():
    with pytest.raises(ValueError):
        calculate_pricing(-1, 1.4)
