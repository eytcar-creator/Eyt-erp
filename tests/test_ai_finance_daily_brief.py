from datetime import date, datetime, timezone
from pathlib import Path

from api.production import ai_finance_api


ROOT = Path(__file__).resolve().parents[1]


class FakeCursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.last_row = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params):
        self.last_row = next(self.rows)

    def fetchone(self):
        return self.last_row


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return FakeCursor(self.rows)


def test_daily_brief_is_read_only_and_labels_unreconciled_cash(monkeypatch):
    stamp = datetime(2026, 10, 16, 9, tzinfo=timezone.utc)
    monkeypatch.setattr(
        ai_finance_api,
        "_connect",
        lambda: FakeConnection([
            (4, 1000, 300, stamp),
            (3, 5000, 2200, 1200, 700, 300, 2, stamp),
            (2, 10000, 6000, 4000, 40.0, stamp),
            (1,),
            (2, 900, stamp),
        ]),
    )

    result = ai_finance_api.daily_brief(as_of=date(2026, 10, 16), window_days=30, _=None)

    assert result["mutations_performed"] is False
    assert result["cash_actuals"]["period_net_movement"] == 700
    assert result["cash_actuals"]["available_cash_balance"] is None
    assert result["cash_actuals"]["status"] == "RECORDED_MOVEMENTS_NOT_RECONCILED_BALANCE"
    assert result["cash_forecast"]["status"] == "INSUFFICIENT_DATA"
    assert result["receivables"]["overdue"] == 2200
    assert result["product_contribution"]["rows_missing_cost"] == 1
    assert result["payables"]["status"] == "PARTIAL_OPEN_ALERTS_ONLY"
    assert {a["action_type"] for a in result["recommended_actions"]} == {
        "COMPLETE_COST_RECORDS",
        "COLLECT_OVERDUE_RECEIVABLES",
    }
    assert result["data_quality"]["status"] == "WARNINGS"
    assert "latest_invoice_date" in result["source_snapshot"]["receivables"]
    assert "updated_at" not in result["source_snapshot"]["receivables"]


def test_daily_brief_route_requires_finance_read_and_has_no_write_routes():
    source = (ROOT / "api/production/ai_finance_api.py").read_text(encoding="utf-8")
    main = (ROOT / "api/production/main.py").read_text(encoding="utf-8")

    assert 'prefix="/api/v1/ai-finance"' in source
    assert '@router.get("/daily-brief")' in source
    assert 'Depends(require_permission("finance.read"))' in source
    assert "from .ai_finance_api import router as ai_finance_router" in main
    assert "profit_dashboard_router, ai_finance_router" in main
    assert '@router.post(' not in source
    assert '@router.put(' not in source
    assert '@router.delete(' not in source
