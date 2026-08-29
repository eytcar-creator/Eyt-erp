from decimal import Decimal

from api.production.dashboard import OperationSnapshot, summarize_operations


def test_dashboard_summary():
    result = summarize_operations([
        OperationSnapshot("CUT", "برش", "completed", accepted_qty=Decimal("2000")),
        OperationSnapshot("FORGE", "فورج", "completed", accepted_qty=Decimal("1970"), rejected_qty=Decimal("20"), waste_qty=Decimal("10")),
        OperationSnapshot("CNC", "CNC", "in_progress"),
    ])
    assert result["total_operations"] == 3
    assert result["completed_operations"] == 2
    assert result["completion_percent"] == Decimal("66.67")
    assert result["waste_qty"] == Decimal("10")
