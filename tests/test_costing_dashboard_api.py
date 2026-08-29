from decimal import Decimal

from api.production.costing import true_cost, unit_cost
from api.production.dashboard import OperationSnapshot, summarize_operations


def test_true_cost_includes_holding_cost_and_prepayment_reduction():
    result = true_cost(
        material=Decimal("1000"),
        subcontracting=Decimal("200"),
        labor=Decimal("100"),
        transport=Decimal("50"),
        overhead=Decimal("50"),
        qc=Decimal("20"),
        scrap=Decimal("30"),
        holding_days=Decimal("10"),
        annual_rate=Decimal("0.365"),
        customer_prepayment=Decimal("500"),
    )
    assert result["gross_cost"] == Decimal("1450")
    assert result["capital_base"] == Decimal("950")
    assert result["holding_cost"] == Decimal("9.50")
    assert result["true_cost"] == Decimal("1459.50")
    assert unit_cost(result["true_cost"], Decimal("100")) == Decimal("14.60")


def test_dashboard_summary_counts_completion_rejection_and_waste():
    result = summarize_operations([
        OperationSnapshot("FORGE", "Forging", "completed", accepted_qty=Decimal("95"), rejected_qty=Decimal("3"), waste_qty=Decimal("2")),
        OperationSnapshot("CNC", "CNC", "in_progress", accepted_qty=Decimal("0")),
    ])
    assert result["total_operations"] == 2
    assert result["completed_operations"] == 1
    assert result["completion_percent"] == Decimal("50.00")
    assert result["operations_with_rejection"] == 1
    assert result["accepted_qty"] == Decimal("95")
    assert result["waste_qty"] == Decimal("2")
